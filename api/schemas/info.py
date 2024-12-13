from pydantic import BaseModel

class GeosResponse(BaseModel):
    available_geos: list[str]
