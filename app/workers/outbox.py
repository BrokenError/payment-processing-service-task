import asyncio
import logging

from faststream.rabbit import RabbitBroker
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db.session import SessionLocal
from app.services.outbox import publish_pending_events

logger = logging.getLogger(__name__)


async def run_outbox_loop(broker: RabbitBroker, stop_event: asyncio.Event) -> None:
    logger.info("Outbox publisher loop started")
    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                published = await publish_pending_events(session, broker)
                if published:
                    logger.info("Published %s outbox event(s)", published)
        except SQLAlchemyError:
            logger.exception("Outbox publisher failed to read/update events")
        except Exception:
            logger.exception("Outbox publisher failed to publish events")

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.outbox_poll_interval_seconds,
            )
        except TimeoutError:
            continue
    logger.info("Outbox publisher loop stopped")
