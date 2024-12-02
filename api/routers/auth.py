from fastapi import APIRouter, Depends, HTTPException, status

from api.core.security import get_current_user, create_access_token
from api.schemas.user import UserCreate, UserLogin, UserCreatedResponse
from database.session import get_db
from database.operations.user_crud import create_user, check_user_exists, authenticate_user
from api.schemas.user import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_user_client(
        form_data: UserLogin,
        db=Depends(get_db)
):
    user = await authenticate_user(db, form_data.login, form_data.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    access_token = create_access_token(
        data={"login": user.login, "is_admin": user.is_admin}
    )
    return Token(access_token=access_token)


@router.post("/create_user", status_code=status.HTTP_201_CREATED, response_model=UserCreatedResponse)
async def create_new_user_client(
        new_user: UserCreate,
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to create a user")

    if await check_user_exists(db, new_user.login.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Such user already exists")

    await create_user(db, new_user)
    token = create_access_token(data={"login": new_user.login, "is_admin": new_user.is_admin})
    return UserCreatedResponse(login=new_user.login, is_admin=new_user.is_admin, access_token=token)




