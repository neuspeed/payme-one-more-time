
import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Depends

from app.api import payments, security
from app.outbox.publisher import run_outbox_publisher
from app.broker.rabbit import broker

@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.start()
    task = asyncio.create_task(run_outbox_publisher())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    await broker.stop()

app = FastAPI(
    title="Async Payment Service",
    dependencies=[Depends(security.verify_api_key)],
    lifespan=lifespan,
    openapi_prefix="/api/v1"
)


app.include_router(payments.router) 