from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# TODO Change to postgres after local testing
DATABASE_URL = r"sqlite+aiosqlite:///D:\fun_project\proxyManager\proxy.sqlite"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


