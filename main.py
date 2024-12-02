from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler


from fastapi import FastAPI
from api.routers.auth import router as auth_router
from api.routers.port import router as v1_router
from api.utils.tasks import waiting_requests_check, handle_expired_port_rents
from dotenv import load_dotenv, find_dotenv

from database.session import SessionLocal


load_dotenv(find_dotenv())


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.start()
    session_for_checks = SessionLocal()
    scheduler.add_job(waiting_requests_check, "interval", seconds=5, args=[session_for_checks])
    scheduler.add_job(handle_expired_port_rents, "interval", seconds=10, args=[session_for_checks])
    yield

    await session_for_checks.close()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(v1_router, prefix="", tags=["v1"])


@app.get("/")
async def root():
    return {"message": "Hello I'm proxy manager"}


if __name__ == "__main__":
    import uvicorn

    # For development purposes
    uvicorn.run(app, host="127.0.0.1", port=8000)
