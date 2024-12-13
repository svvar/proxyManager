import datetime
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, update, not_, func, or_, and_, case, bindparam
from sqlalchemy.orm import aliased

from database.models import Ports, Sellers, Geos, ProxyTypes, Requests, Responses, PortResponses, IPInfo
from database.session import SessionLocal, engine


async def get_sellers():
    async with SessionLocal() as session:
        query = select(Sellers)
        result = await session.execute(query)
        return result.scalars().all()

async def get_seller(seller_id: int):
    async with SessionLocal() as session:
        query = select(Sellers).where(Sellers.seller_id == seller_id)
        result = await session.execute(query)
        return result.scalars().first()


async def add_seller(mark: str, login: str, password: str, site_link: str):
    async with SessionLocal() as session:
        query = insert(Sellers).values(mark=mark, login=login, password=password, site_link=site_link)
        await session.execute(query)
        await session.commit()


async def delete_seller(seller_id: int):
    async with SessionLocal() as session:
        result = await session.execute(
            delete(Sellers).where(Sellers.seller_id == seller_id)
            .returning(Sellers.seller_id)
        )

        return result.scalar()


async def get_ports():
    async with SessionLocal() as session:
        query = select(Ports)
        result = await session.execute(query)
        return result.scalars().all()


async def get_port(port_id: int):
    async with SessionLocal() as session:
        query = select(Ports).where(Ports.port_id == port_id)
        result = await session.execute(query)
        return result.scalars().first()


async def add_port(data: dict):
    async with SessionLocal() as session:
        res = await session.execute(insert(Ports).values(**data).returning(Ports.port_id))
        await session.commit()
        return res.scalar()


async def add_port_ip_version(port_id: int, ip_version: int):
    async with SessionLocal() as session:
        await session.execute(update(Ports).where(Ports.port_id == port_id).values(ip_version=ip_version))
        await session.commit()


async def delete_port(port_id: int):
    async with SessionLocal() as session:
        await session.execute(delete(Ports).where(Ports.port_id == port_id))
        await session.commit()

async def get_sellers_ports(seller_id: int):
    async with SessionLocal() as session:
        query = select(Ports).where(Ports.seller_id == seller_id)
        result = await session.execute(query)
        return result.scalars().all()


async def flip_port_status(port_id: int):
    async with SessionLocal() as session:
        stmt = await session.execute(
            update(Ports)
            .where(Ports.port_id == port_id)
            .values(is_active=not_(Ports.is_active))
            .returning(Ports.is_active))
        await session.commit()
        return stmt.scalar()



async def get_geos():
    async with SessionLocal() as session:
        query = select(Geos)
        result = await session.execute(query)
        return result.scalars().all()


async def get_proxy_types():
    async with SessionLocal() as session:
        query = select(ProxyTypes)
        result = await session.execute(query)
        return result.scalars().all()


async def add_geo(geo: str):
    async with SessionLocal() as session:
        await session.execute(insert(Geos).values(name=geo))
        await session.commit()


async def add_proxy_type(proxy_type: str):
    async with SessionLocal() as session:
        await session.execute(insert(ProxyTypes).values(name=proxy_type))
        await session.commit()


async def delete_geo(geo_id: int):
    async with SessionLocal() as session:
        await session.execute(delete(Geos).where(Geos.geo_id == geo_id))
        await session.commit()


async def delete_proxy_type(proxy_type_id: int):
    async with SessionLocal() as session:
        await session.execute(delete(ProxyTypes).where(ProxyTypes.proxy_type_id == proxy_type_id))
        await session.commit()


async def count_requests(start_date: datetime, end_date: datetime):
    async with SessionLocal() as session:
        if start_date == end_date:
            query = select(func.count(Requests.request_id)).where(func.DATE(Requests.created_at) == start_date)
        else:
            query = select(func.count(Requests.request_id)).where(func.DATE(Requests.created_at) >= start_date, func.DATE(Requests.created_at) <= end_date)

        result = await session.execute(query)
        return result.scalar()


async def get_rent_end_times():
    async with SessionLocal() as session:
        query = select(Ports.port_id, Ports.rent_end)
        result = await session.execute(query)
        return result.all()



async def get_busy_time_for_port(
    start_date: datetime,
    end_date: datetime,
    port_id: int
) -> float:
    """
    Asynchronously calculate the total busy time in seconds for a specific port within the specified UTC date range.

    Parameters:
        session (AsyncSession): SQLAlchemy asynchronous session object.
        start_date (datetime.datetime): Start of the date range (inclusive). Must be timezone-aware UTC.
        end_date (datetime.datetime): End of the date range (exclusive). Must be timezone-aware UTC.
        port_id (int): The ID of the port for which to calculate the busy time.

    Returns:
        float: Total busy time in seconds for the specified port within the date range.
    """

    async with SessionLocal() as session:
        # Bind parameters
        interval_start_param = bindparam('interval_start', value=start_date)
        interval_end_param = bindparam('interval_end', value=end_date)
        port_id_param = bindparam('port_id', value=port_id)

        base_query = (
            select(Responses, IPInfo)
            .select_from(Responses)
            .join(IPInfo, Responses.ip_info_id == IPInfo.ip_info_id)
            .where(
                IPInfo.port_id == port_id_param,
                Responses.rent_ended_at.isnot(None),
                Responses.rent_ended_at >= interval_start_param,
                Responses.created_at <= interval_end_param,
            )
        )

        if engine.name == 'sqlite':
            # SQLite uses MAX and MIN instead of GREATEST and LEAST
            overlap_start = func.max(Responses.created_at, interval_start_param)
            overlap_end = func.min(Responses.rent_ended_at, interval_end_param)

            duration_expr = (func.julianday(overlap_end) - func.julianday(overlap_start)) * 86400.0
        else:
            # PostgreSQL uses GREATEST and LEAST functions
            overlap_start = func.greatest(Responses.created_at, interval_start_param)
            overlap_end = func.least(Responses.rent_ended_at, interval_end_param)

            duration_expr = func.extract('epoch', overlap_end - overlap_start)

        # Sum the durations over all matching responses
        total_busy_time_seconds = func.sum(duration_expr)

        # Construct the final query
        query = base_query.with_only_columns(total_busy_time_seconds)

        result = await session.execute(
            query,
            {
                'port_id': port_id,
                'interval_start': start_date,
                'interval_end': end_date,
            },
        )

        return result.scalar() or 0  # Handle None result

