from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# TODO Change to postgres after local testing
DATABASE_URL = r"sqlite+aiosqlite:///D:\fun_project\proxyManager\proxy.sqlite"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


