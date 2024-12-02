from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    login: str
    password: str
    is_admin: bool = False


    @field_validator('login', 'password')
    @classmethod
    def validate_fields(cls, v):
        v_str = str(v)
        if not v_str.strip():
            raise ValueError('This field cannot be empty')
        return v_str


class UserLogin(BaseModel):
    login: str
    password: str

    @field_validator('login', 'password')
    @classmethod
    def validate_fields(cls, v):
        v_str = str(v)
        if not v_str.strip():
            raise ValueError('This field cannot be empty')
        return v_str


class User(BaseModel):
    login: str
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreatedResponse(User, Token):
    pass
