from datetime import datetime, timedelta

from aiohttp import ClientSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.utils.glweb_ports import glweb_synchronize
from api.utils.ip_requests import rotate_proxy, get_socks_proxy_ip, get_ip_info, get_http_proxy_ip_multitry
from database.operations.api_port_transactions import check_waiting_requests, free_missed_port, get_expired_responses, \
    get_port_for_rotation, create_new_ip_info, delete_port_response, finish_request_and_response, get_waiting_requests
from database.operations.website_sync_operations import get_all_sellers, get_geo_id, get_sync_status
from database.session import SessionLocal

scheduler = AsyncIOScheduler()


async def waiting_requests_check():
    waiting_requests = await get_waiting_requests()

    found_ports = await check_waiting_requests(waiting_requests)

    run_time = datetime.now() + timedelta(seconds=60)
    for port_response_id in found_ports:
        scheduler.add_job(free_missed_port, "date", run_date=run_time, args=[port_response_id])


async def handle_expired_port_rents():
    response_ids = await get_expired_responses()

    if not response_ids:
        return

    http_session = ClientSession()

    # Didn't use asyncio.gather here, not to overload the server with transactions/requests
    for response_id in response_ids:
        await end_proxy_port_rent(response_id, http_session)


async def end_proxy_port_rent(
        response_id: int,
        http_session: ClientSession = None
):

    db = SessionLocal()
    if not http_session:
        http_session = ClientSession()

    async with db, http_session:
        await finish_request_and_response(response_id)
        port = await get_port_for_rotation(response_id)

        if port and port.rotation_link:
            await rotate_proxy(http_session, port.rotation_link)
            if port.http_port:
                ip, ip_ver = await get_http_proxy_ip_multitry(http_session, port.host, port.http_port, port.login, port.password)
            else:
                ip, ip_ver = await get_socks_proxy_ip(port.host, port.socks_port, port.login, port.password)
            print(ip, ip_ver)
            if ip:
                ip_info = await get_ip_info(http_session, ip)
                await create_new_ip_info(port.port_id, ip_info['ip'], ip_ver, ip_info['city'], ip_info['region'], ip_info['org'])

        # if port.rotation_type == RotationType.STATIC:
        #     pass

        await delete_port_response(response_id)


async def synchronize_ports():
    if not await get_sync_status():
        return
    all_sellers = await get_all_sellers()
    for s in all_sellers:
        if 'glweb.studio' in s.site_link:
            geo = 'ua'
            geo_id = await get_geo_id(geo)
            await glweb_synchronize(s.seller_id, geo_id, s.login, s.password)

