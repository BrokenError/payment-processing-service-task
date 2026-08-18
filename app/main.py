import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.broker.topology import create_broker, declare_topology
from app.core.logging import configure_logging
from app.workers.outbox import run_outbox_loop

logger = logging.getLogger(__name__)


def create_app(*, enable_outbox: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        if not enable_outbox:
            yield
            return

        stop_event = asyncio.Event()
        broker = create_broker()
        await broker.start()
        await declare_topology(broker)
        outbox_task = asyncio.create_task(
            run_outbox_loop(broker, stop_event),
            name="outbox-publisher",
        )
        logger.info("API started, outbox publisher is running")
        try:
            yield
        finally:
            stop_event.set()
            await outbox_task
            await broker.close()
            logger.info("API stopped")

    application = FastAPI(
        title="Payment Processing Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(v1_router)

    @application.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
