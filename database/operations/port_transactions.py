from datetime import timedelta, datetime

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, or_, func, exists, and_
from sqlalchemy.dialects.postgresql import insert as upsert_insert

from database import models
from api.schemas.port import PortRequest
from database.enums import RequestStatus, ResponseStatus


async def write_request(session: AsyncSession, request: PortRequest, requester_login: str):
    async with session:
        result = await session.execute(insert(models.Requests).values(
            servername=request.servername,
            priority=request.priority,
            geo=request.geo,
            ip_version=request.ip_version,
            rent_time=request.rent_time,
            login=requester_login

        ).returning(models.Requests.request_id))
        await session.commit()
        return result.scalars().first()


async def is_same_request(session: AsyncSession, request: PortRequest, requester_login: str):
    async with session:
        result = await session.execute(
            select(models.Requests.request_id)
            .where(models.Requests.servername == request.servername)  # type: ignore
            .where(models.Requests.login == requester_login)           # type: ignore
            .where(models.Requests.geo == request.geo)                # type: ignore
            .where(models.Requests.ip_version == request.ip_version)  # type: ignore
            .where(or_(models.Requests.status == RequestStatus.WAITING_FOR_PORT, models.Requests.status == RequestStatus.PORT_WAITING))
            .order_by(models.Requests.created_at.desc())
            .limit(1)
        )

        return result.scalar()


async def allocate_port(session: AsyncSession, request: PortRequest, request_id: int):
    async with session.begin():
        # Step 1: Find and Lock a Free Port
        port_subquery = (
            select(models.PortResponses.port_id)
            .subquery()
        )

        port_query = (
            select(models.Ports)
            .join(models.Geos)
            .where(models.Ports.is_active.is_(True))
            .where(models.Geos.name == request.geo)                                                       # type: ignore
            .where(models.Ports.ip_version == request.ip_version if request.ip_version != 0 else True)
            .where(models.Ports.port_id.notin_(port_subquery))
            .with_for_update(skip_locked=True)  # Skip ports locked by other transactions
            .limit(1)
        )

        port_result = await session.execute(port_query)
        port = port_result.scalar_one_or_none()

        if not port:
            return None, None, None

        # Step 2: Get Latest IP Info
        ip_info_query = (
            select(models.IPInfo)
            .where(models.IPInfo.port_id == port.port_id)
            .order_by(models.IPInfo.created_at.desc())
            .limit(1)
        )

        ip_info_result = await session.execute(ip_info_query)
        ip_info = ip_info_result.scalar_one_or_none()

        if not ip_info:
            return None, None, None

        # Step 3: Update Request Status
        await session.execute(
            update(models.Requests)
            .where(models.Requests.request_id == request_id)         # type: ignore
            .values(status=RequestStatus.SUCCESS)
        )

        # Step 4: Create Response
        response_insert = insert(models.Responses).values(
            parent_request_id=request_id,
            ip_info_id=ip_info.ip_info_id,
            status=ResponseStatus.SUCCESS
        ).returning(models.Responses.response_id, models.Responses.created_at)

        response_result = await session.execute(response_insert)
        response = response_result.scalar_one_or_none()
        # response_id, response_created_at = response.response_id, response.created_at

        # Step 5: Create Port Response
        port_response_insert = insert(models.PortResponses).values(
            response_id=response.response_id,
            port_id=port.port_id,
            end_timestamp_utc=response.response_created_at + timedelta(seconds=request.rent_time)
        ).returning(models.PortResponses.end_timestamp_utc)

        port_response_result = await session.execute(port_response_insert)
        end_timestamp_utc = port_response_result.scalar()

        return port, end_timestamp_utc, response.response_id


async def is_waiting_for_port(session: AsyncSession, client_login: str, request: PortRequest):
    async with session:
        result = await session.execute(
            select(models.Requests)
            .where(models.Requests.login == client_login)             # type: ignore
            .where(models.Requests.status == RequestStatus.WAITING_FOR_PORT)
            .where(models.Requests.geo == request.geo)                # type: ignore
            .where(models.Requests.ip_version == request.ip_version)  # type: ignore
        )
        return result.scalars().first() is not None


async def set_waiting_for_port(session: AsyncSession, request_id: int):
    async with session:
        await session.execute(
            update(models.Requests)
            .where(models.Requests.request_id == request_id)
            .values(status=RequestStatus.WAITING_FOR_PORT)
        )
        await session.commit()


async def give_port_if_found(session: AsyncSession, request_id: int, new_rent_time: int):
    async with session.begin():
        response_id_subquery = (
            select(models.Responses.response_id)
            .where(models.Responses.parent_request_id == request_id)
            .subquery()
        )

        target_port_response = await session.execute(
            select(models.PortResponses)
            .join(models.Responses)
            .where(models.Responses.response_id == response_id_subquery)
            .where(models.Responses.status == ResponseStatus.PORT_WAITING)
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        port_response = target_port_response.scalar_one_or_none()
        if not port_response:
            return None, None, None


        update_timeout = await session.execute(
            update(models.PortResponses)
            .where(models.PortResponses.port_response_id == port_response.port_response_id)
            .values(end_timestamp_utc=datetime.utcnow() + timedelta(seconds=new_rent_time))
            .returning(models.PortResponses.end_timestamp_utc)
        )

        end_time = update_timeout.scalar()

        port_query = await session.execute(
            select(models.Ports)
            .where(models.Ports.port_id == port_response.port_id)
        )
        port = port_query.scalar_one_or_none()

        response_update = await session.execute(
            update(models.Responses)
            .where(models.Responses.response_id == response_id_subquery)
            .values(status=ResponseStatus.SUCCESS)
            .returning(models.Responses.response_id)
        )
        response_id = response_update.scalar()

        await session.execute(
            update(models.Requests)
            .where(models.Requests.request_id == request_id)
            .values(status=RequestStatus.SUCCESS)
        )

        return port, end_time, response_id


#####
# Port end
#####

async def check_response_existence(session: AsyncSession, response_id: int, user_login: str):
    async with session:
        exists_query = await session.execute(
            select(models.Responses)
            .join(models.Requests)
            .where(models.Responses.response_id == response_id)
            .where(models.Requests.login == user_login)
        )
        exists = exists_query.scalar_one_or_none()

        return True if exists else False


async def check_rent_already_ended(session: AsyncSession, response_id: int):
    async with session:
        result_query = await session.execute(
            select(models.PortResponses)
            .join(models.Responses)
            .where(models.Responses.response_id == response_id)
        )
        result = result_query.scalar_one_or_none()

        return True if result else False


async def finish_request_and_response(session: AsyncSession, response_id: int):
    async with session.begin():
        update_response = await session.execute(
            update(models.Responses)
            .where(models.Responses.response_id == response_id)
            .values(status=ResponseStatus.FINISHED)
            .returning(models.Responses.parent_request_id)
        )

        parent_request_id = update_response.scalar()

        await session.execute(
            update(models.Requests)
            .where(models.Requests.request_id == parent_request_id)
            .values(status=RequestStatus.FINISHED)
        )


async def get_port_for_rotation(session: AsyncSession, response_id: int):
    async with session:
        port_query = await session.execute(
            select(models.Ports)
            .join(models.PortResponses)
            .join(models.Responses)
            .where(models.PortResponses.port_id == response_id)
        )

        return port_query.scalar_one_or_none()


# async def check_static_has_ip_info(session: AsyncSession, port_id: int):
#     async with session:
#         result = await session.execute(
#             select(models.IPInfo)
#             .where(models.IPInfo.port_id == port_id)
#         )
#         return result.scalar()


async def create_new_ip_info(session: AsyncSession, port_id: int, ip: str, ip_version: int, city: str, region: str, operator: str):
    async with session.begin():
        operator_stmt = (
            upsert_insert(models.Operators)
            .values(operator=operator)
            .on_conflict_do_update(index_elements=['operator'], set_=dict(operator=models.Operators.operator))
            .returning(models.Operators.operator_id)
        )
        operator_result = await session.execute(operator_stmt)
        operator_id = operator_result.scalar()

        city_stmt = (
            upsert_insert(models.Cities)
            .values(city=city, region=region)
            .on_conflict_do_update(index_elements=['city', 'region'], set_=dict(city=models.Cities.city, region=models.Cities.region))
            .returning(models.Cities.city_id)
        )
        city_result = await session.execute(city_stmt)
        city_id = city_result.scalar()

        await session.execute(
            insert(models.IPInfo).values(
                port_id=port_id,
                ip=ip,
                ip_version=ip_version,
                operator_id=operator_id,
                city_id=city_id
            )
        )


async def delete_port_response(session: AsyncSession, response_id: int):
    async with session:
        await session.execute(
            delete(models.PortResponses)
            .where(models.PortResponses.response_id == response_id)
        )

        await session.commit()



######
# Automatic utils
######

async def check_waiting_requests(session: AsyncSession):
    print("Checking for waiting requests...")
    waiting_requests = await session.execute(
        select(models.Requests)
        .where(models.Requests.status == RequestStatus.WAITING_FOR_PORT)        # type: ignore
        .order_by(models.Requests.created_at.asc(), models.Requests.priority.desc())
    )

    waiting_requests = waiting_requests.all()

    check_after_60_sec = []

    for request in waiting_requests:
        print(f"Processing request {request.request_id}")
        async with session.begin():
            # Step 1: Find and Lock a Free Port
            port_subquery = (
                select(models.PortResponses.port_id)
                .subquery()
            )

            port_query = (
                select(models.Ports.port_id)
                .join(models.Geos)
                .where(models.Ports.is_active.is_(True))
                .where(models.Geos.name == request.geo)
                .where(models.Ports.ip_version == request.ip_version if request.ip_version != 0 else True)
                .where(models.Ports.port_id.notin_(port_subquery))
                .with_for_update(skip_locked=True)  # Skip ports locked by other transactions
                .limit(1)
            )

            port_result = await session.execute(port_query)
            port_id = port_result.scalar_one_or_none()

            if not port_id:
                continue

            # Step 2: Get Latest IP Info
            ip_info_query = (
                select(models.IPInfo)
                .where(models.IPInfo.port_id == port_id)
                .order_by(models.IPInfo.created_at.desc())
                .limit(1)
            )

            ip_info_result = await session.execute(ip_info_query)
            ip_info = ip_info_result.scalar_one_or_none()

            if not ip_info:
                continue

            # Step 3: Update Request Status
            await session.execute(
                update(models.Requests)
                .where(models.Requests.request_id == request.request_id)
                .values(status=RequestStatus.PORT_WAITING)
            )

            # Step 4: Create Response
            response_insert = insert(models.Responses).values(
                parent_request_id=request.request_id,
                ip_info_id=ip_info.ip_info_id,
                status=ResponseStatus.PORT_WAITING
            ).returning(models.Responses.response_id, models.Responses.created_at)

            response_result = await session.execute(response_insert)
            response_row = response_result.fetchone()
            response_id, response_created_at = response_row

            # Step 5: Create Port Response
            port_response_insert = insert(models.PortResponses).values(
                response_id=response_id,
                port_id=port_id,
                end_timestamp_utc=response_created_at + timedelta(seconds=60)
            ).returning(models.PortResponses.port_response_id)

            port_response = await session.execute(port_response_insert)
            check_after_60_sec.append(port_response.scalar())

    return check_after_60_sec


async def free_missed_port(session: AsyncSession, port_response_id: int):
    async with session.begin():
        port_response = await session.execute(
            select(models.PortResponses.port_response_id, models.PortResponses.response.id, models.Responses.parent_request_id)
            .join(models.Responses)
            .where(models.PortResponses.port_response_id == port_response_id)
            .where(models.Responses.status == ResponseStatus.PORT_WAITING)
        )
        port_response = port_response.first()

        if port_response:
            port_response_id, response_id, request_id = port_response

            await session.execute(
                delete(models.PortResponses)
                .where(models.PortResponses.port_response_id == port_response_id)
            )

            await session.execute(
                update(models.Requests)
                .where(models.Requests.request_id == request_id)
                .values(status=RequestStatus.MISSED)
            )

            await session.execute(
                update(models.Responses)
                .where(models.Responses.response_id == response_id)
                .values(status=RequestStatus.MISSED)
            )


async def get_expired_responses(session: AsyncSession):
    async with session:
        result = await session.execute(
            select(models.Responses.response_id)
            .join(models.PortResponses)
            .where(models.PortResponses.end_timestamp_utc < datetime.utcnow())
        )

        return result.all()
