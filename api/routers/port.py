from fastapi import APIRouter, Depends, BackgroundTasks

from api.core.security import get_current_user
from database.session import get_db, SessionLocal
from api.schemas.port import PortRequest, PortResponse, ErrorResponse, SuccessResponse, PortData
from database.operations.api_port_transactions import (write_request, is_waiting_for_port, set_waiting_for_port, allocate_port,
                                                       is_same_request, give_port_if_found, check_response_existence, check_rent_already_ended,
                                                       )

from api.utils.tasks import end_proxy_port_rent

router = APIRouter()


# get_current_user = lambda: "user1"


# TODO define possible responses and codes inside get()
@router.get("/getport")
async def get_proxy_port(
        port_request: PortRequest = Depends(),
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):

    same_request_id = await is_same_request(port_request, current_user)         # current_user.login
    if same_request_id:
        port, end_time, response_id = await give_port_if_found(db, same_request_id, port_request.rent_time)
        if port:
            return PortResponse(order_id=response_id,
                                data=PortData(
                                    host=port.host,
                                    socks_port=port.socks_port,
                                    http_port=port.http_port,
                                    login=port.login,
                                    password=port.password,
                                    end_timestamp_utc=end_time
                                ))
        else:
            return ErrorResponse(success=False, error="No port is available for this request. Please try again later.")

    else:
        request_id = await write_request(db, port_request, current_user)    # current_user.login
        port, end_time, response_id = await allocate_port(db, port_request, request_id)

        if port:
            return PortResponse(order_id=response_id,
                                data=PortData(
                                    host=port.host,
                                    socks_port=port.socks_port,
                                    http_port=port.http_port,
                                    login=port.login,
                                    password=port.password,
                                    end_timestamp_utc=end_time
                                ))
        else:
            waiting_for_port = await is_waiting_for_port(db, current_user, port_request)
            if not waiting_for_port:
                await set_waiting_for_port(db, request_id)

            return ErrorResponse(success=False, error="No port is available for this request. Please try again later.")


# TODO define possible responses and codes inside get()
@router.get("/endport")
async def end_port(
        order_id: int,
        background_tasks: BackgroundTasks,
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    if not await check_response_existence(db, order_id, current_user):    # current_user.login
        return ErrorResponse(success=False, error="No such order found")

    if not await check_rent_already_ended(db, order_id):    # current_user.login
        return ErrorResponse(success=False, error="This order was already ended")

    background_tasks.add_task(end_proxy_port_rent, order_id)

    return SuccessResponse(message="The rent was successfully ended")
