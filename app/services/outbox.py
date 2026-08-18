import logging
from datetime import UTC, datetime

from faststream.rabbit import RabbitBroker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker.topology import PAYMENTS_EXCHANGE, PAYMENTS_NEW_ROUTING_KEY
from app.config import settings
from app.models.outbox import OutboxEvent
from app.schemas.events import PaymentCreatedEvent

logger = logging.getLogger(__name__)


async def publish_pending_events(session: AsyncSession, broker: RabbitBroker) -> int:
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(settings.outbox_batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list(await session.scalars(stmt))
    published = 0

    for event in events:
        try:
            payload = PaymentCreatedEvent.model_validate(event.payload)
            await broker.publish(
                payload,
                exchange=PAYMENTS_EXCHANGE,
                routing_key=PAYMENTS_NEW_ROUTING_KEY,
                persist=True,
                message_id=str(event.id),
            )
            event.published_at = datetime.now(UTC)
            await session.commit()
            published += 1
            logger.info("Published outbox event %s (%s)", event.id, event.event_type)
        except Exception:
            await session.rollback()
            logger.exception("Failed to publish outbox event %s", event.id)
            break

    return published
