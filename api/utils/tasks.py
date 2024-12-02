from datetime import datetime, timedelta

from aiohttp import ClientSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.requests import rotate_proxy, get_http_proxy_ip, get_socks_proxy_ip, get_ip_info
from database.operations.port_transactions import check_waiting_requests, free_missed_port, get_expired_responses, \
    get_port_for_rotation, create_new_ip_info, delete_port_response, finish_request_and_response
from database.session import SessionLocal

scheduler = AsyncIOScheduler()


async def waiting_requests_check(session: AsyncSession):
    found_ports = await check_waiting_requests(session)

    run_time = datetime.now() + timedelta(seconds=60)
    for port_response_id in found_ports:
        scheduler.add_job(free_missed_port, "date", run_date=run_time, args=[session, port_response_id])


async def handle_expired_port_rents(session: AsyncSession):
    response_ids = await get_expired_responses(session)

    if not response_ids:
        return

    db = SessionLocal()
    http_session = ClientSession()

    # Didn't use asyncio.gather here, not to overload the server with transactions/requests
    for response_id in response_ids:
        await end_proxy_port_rent(response_id, db, http_session)


async def end_proxy_port_rent(
        response_id: int,
        db: AsyncSession = SessionLocal(),
        http_session: ClientSession = ClientSession()
):
    async with db, http_session:
        await finish_request_and_response(db, response_id)
        port = await get_port_for_rotation(db, response_id)

        if port and port.rotation_link:
            await rotate_proxy(http_session, port.rotation_link)
            if port.http_port:
                ip = await get_http_proxy_ip(http_session, port.host, port.http_port, port.login, port.password, port.ip_version)
            else:
                ip = await get_socks_proxy_ip(port.host, port.socks_port, port.login, port.password, port.ip_version)

            if ip:
                ip_info = await get_ip_info(http_session, ip)
                await create_new_ip_info(db, port.id, ip_info['ip'], port.ip_version, ip_info['city'], ip_info['region'], ip_info['org'])

        # if port.rotation_type == RotationType.STATIC:
        #     pass

        await delete_port_response(db, response_id)
