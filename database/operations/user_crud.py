from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from api.schemas.user import UserCreate
from database.models import Users as UserDB
from api.core.security import get_password_hash, verify_password


async def create_user(session: AsyncSession, user_data: UserCreate):
    hashed_password = get_password_hash(user_data.password)
    async with session:
        await session.execute(insert(UserDB).values(
            login=user_data.login,
            password=hashed_password,
            is_admin=user_data.is_admin
        ).returning(UserDB.user_id))
        await session.commit()


async def check_user_exists(session: AsyncSession, login: str):
    user = await session.execute(select(UserDB).where(UserDB.login == login))                 # type: ignore
    user = user.scalars().first()
    return user


async def authenticate_user(session: AsyncSession, login: str, password: str):
    user = await session.execute(select(UserDB).where(UserDB.login == login))                 # type: ignore
    user = user.scalars().first()
    if user and verify_password(password, user.password):
        return user
    return None
