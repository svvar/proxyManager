import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn
from fastapi import FastAPI

from api.routers.auth import router as auth_router
from api.routers.port import router as v1_router
from api.routers.info import info_router
from api.utils.tasks import waiting_requests_check, handle_expired_port_rents, synchronize_ports



@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(waiting_requests_check, "interval", seconds=5)
    scheduler.add_job(handle_expired_port_rents, "interval", seconds=10)
    scheduler.add_job(synchronize_ports, "interval", minutes=30)
    scheduler.start()
    yield

    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(v1_router, prefix="", tags=["v1"])
app.include_router(info_router, prefix="/info", tags=["info"])


@app.get("/")
async def root():
    return {"message": "Hello I'm proxy manager"}


async def run_uvicorn_from_async(host: str = "127.0.0.1", port: int = 8000):
    config = uvicorn.Config(app=app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_uvicorn_from_async())
