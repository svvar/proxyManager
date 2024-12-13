import asyncio

import aiohttp
from aiohttp import ClientSession
from sqlalchemy import select, insert, update

from api.utils.ip_requests import get_ip_info, get_http_proxy_ip_multitry
from database.models import Ports, Sellers, Geos, SyncStatus
from database.operations.bot_operations import add_port_ip_version, delete_port
from database.session import SessionLocal

from database.operations.api_port_transactions import create_new_ip_info


async def autosync_on():
    async with SessionLocal() as session:
        await session.execute(
            update(SyncStatus)
            .values(sync_on=True)
        )
        await session.commit()


async def autosync_off():
    async with SessionLocal() as session:
        await session.execute(
            update(SyncStatus)
            .values(sync_on=False)
        )
        await session.commit()


async def get_sync_status():
    async with SessionLocal() as session:
        query = select(SyncStatus.sync_on)
        status = await session.execute(query)
        return status.scalar()


async def get_all_sellers():
    async with SessionLocal() as session:
        query = select(Sellers)
        sellers = await session.execute(query)
        return sellers.scalars().all()


async def get_geo_id(geo: str):
    async with SessionLocal() as session:
        query = select(Geos.geo_id).where(Geos.name == geo)
        geo_id = await session.execute(query)
        result = geo_id.scalar()
        if result:
            return result

        insert_geo = await session.execute(
            insert(Geos)
            .values(name=geo)
            .returning(Geos.geo_id)
        )
        return insert_geo.scalar()


async def upsert_update_ports(seller_id: int, ports: list[dict]):
    updated_port_ids = []
    inserted_port_ids = []
    inserted_ports = []


    for port in ports:
        update_returned = await update_port(seller_id, port)
        if update_returned:
            updated_port_ids.append(update_returned)
        else:
            inserted_port = await insert_port(seller_id, port)
            inserted_ports.append(inserted_port)

    if inserted_ports:
        tasks = []

        connector = aiohttp.TCPConnector(limit=95)
        http_session = ClientSession(connector=connector)
        for inserted_port in inserted_ports:
            tasks.append(get_and_save_ip_info(inserted_port, http_session))


        for task in asyncio.as_completed(tasks, timeout=80):        # Timeout is higher than the one in get_http_proxy_ip so no exception catching
            port_id, is_inserted = await task
            print(port_id, is_inserted)
            if is_inserted:
                inserted_port_ids.append(port_id)

        # results = await asyncio.gather(*tasks)
        # for result in results:
        #     if result[1]:
        #         inserted_port_id = result[0]
        #         inserted_port_ids.append(inserted_port_id)

        await http_session.close()

    return updated_port_ids + inserted_port_ids


async def update_port(seller_id: int, port: dict):
    async with SessionLocal() as session:
        update_query = await session.execute(
            update(Ports)
            .where(Ports.host == port['host'], Ports.socks_port == port['socks_port'],
                   Ports.http_port == port['http_port'], Ports.seller_id == seller_id)
            .values(login=port['login'], password=port['password'], rotation_link=port['rotation_link'],
                    rent_end=port['rent_end'])
            .returning(Ports.port_id)
        )
        returned_id = update_query.scalar()
        await session.commit()
        return returned_id


async def insert_port(seller_id: int, port: dict):
    async with SessionLocal() as session:
        insert_query = await session.execute(
            insert(Ports)
            .values(**port, seller_id=seller_id, is_active=True)
            .returning(Ports)
        )

        inserted_port = insert_query.scalars().first()
        await session.commit()
        return inserted_port


async def get_and_save_ip_info(port: Ports, http_session: ClientSession):
    port_id = port.port_id
    ip, ip_ver = await get_http_proxy_ip_multitry(http_session, port.host, port.http_port, port.login, port.password)
    if ip:
        await add_port_ip_version(port.port_id, ip_ver)
        ip_info = await get_ip_info(http_session, ip)
        await create_new_ip_info(port.port_id, ip_info['ip'], ip_ver, ip_info['city'], ip_info['region'],
                                 ip_info['org'])
        return port_id, True
    else:
        await delete_port(port.port_id)
        return port_id, False


async def deactivate_ports(seller_id: int, port_ids: list):
    async with SessionLocal() as session:
        await session.execute(
            update(Ports)
            .where(Ports.seller_id == seller_id, Ports.port_id.in_(port_ids))
            .values(is_active=False)
        )
        await session.commit()

