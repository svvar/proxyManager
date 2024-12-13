from fastapi import APIRouter, Depends

from database.operations.bot_operations import get_geos as get_geos_db
from api.schemas.info import GeosResponse

info_router = APIRouter()

@info_router.get("/geos", response_model=GeosResponse)
async def get_geos():
    available_geos = await get_geos_db()
    geo_names = [geo.name for geo in available_geos]
    return GeosResponse(available_geos=geo_names)


