from pydantic import BaseModel, field_validator


class PortRequest(BaseModel):
    servername: str
    priority: int
    geo: str
    ip_version: int = 0
    rent_time: int = 600

    @field_validator('servername', 'geo')
    @classmethod
    def validate_fields(cls, v):
        v_str = str(v)
        if not v_str.strip():
            raise ValueError('This field cannot be empty')
        return v_str


    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Priority must be in range 1-10')
        return v

    @field_validator('ip_version')
    @classmethod
    def validate_ip_version(cls, v):
        if v not in [0, 4, 6]:
            raise ValueError('IP version must be 4 or 6. 0 for both')
        return v


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


class SuccessResponse(BaseModel):
    success: bool = True
    message: str | None = None


class PortData(BaseModel):
    host: str
    socks_port: str
    http_port: str
    login: str
    password: str
    end_timestamp_utc: str


class PortResponse(BaseModel):
    success: bool = True
    order_id: int
    data: PortData

