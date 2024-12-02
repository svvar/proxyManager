from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, update, not_

from database.models import Ports, Sellers, Geos, ProxyTypes


async def get_sellers(session: AsyncSession):
    async with session:
        query = select(Sellers)
        result = await session.execute(query)
        return result.scalars().all()

async def get_seller(session: AsyncSession, seller_id: int):
    async with session:
        query = select(Sellers).where(Sellers.seller_id == seller_id)
        result = await session.execute(query)
        return result.scalars().first()


async def add_seller(session: AsyncSession, mark: str, login: str, password: str, site_link: str):
    async with session:
        query = insert(Sellers).values(mark=mark, login=login, password=password, site_link=site_link)
        await session.execute(query)
        await session.commit()


async def delete_seller(session: AsyncSession, seller_id: int):
    async with session:
        result = await session.execute(
            delete(Sellers).where(Sellers.seller_id == seller_id)
            .returning(Sellers.seller_id)
        )

        return result.scalar()


async def get_ports(session: AsyncSession):
    async with session:
        query = select(Ports)
        result = await session.execute(query)
        return result.scalars().all()


async def add_port(session: AsyncSession, data: dict):
    async with session:
        await session.execute(insert(Ports).values(**data))
        await session.commit()


async def get_sellers_ports(session: AsyncSession, seller_id: int):
    async with session:
        query = select(Ports).where(Ports.seller_id == seller_id)
        result = await session.execute(query)
        return result.scalars().all()


async def flip_port_status(session: AsyncSession, port_id: int):
    async with session:
        stmt = await session.execute(
            update(Ports)
            .where(Ports.port_id == port_id)
            .values(is_active=not_(Ports.is_active))
            .returning(Ports.is_active))
        await session.commit()
        return stmt.scalar()



async def get_geos(session: AsyncSession):
    async with session:
        query = select(Geos)
        result = await session.execute(query)
        return result.scalars().all()


async def get_proxy_types(session: AsyncSession):
    async with session:
        query = select(ProxyTypes)
        result = await session.execute(query)
        return result.scalars().all()






