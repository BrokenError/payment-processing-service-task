import logging

from faststream import FastStream, Logger
from faststream.exceptions import AckMessage, RejectMessage
from faststream.rabbit.annotations import RabbitMessage

from app.broker.topology import (
    PAYMENTS_EXCHANGE,
    PAYMENTS_NEW_QUEUE,
    create_broker,
    declare_topology,
    retry_routing_key,
    should_dead_letter,
)
from app.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.schemas.events import PaymentCreatedEvent
from app.services.processor import process_payment
from app.services.webhook import send_webhook

configure_logging()
logger = logging.getLogger(__name__)

broker = create_broker()
app = FastStream(broker)


@app.after_startup
async def on_startup() -> None:
    await declare_topology(broker)
    logger.info("Payment consumer started")


@broker.subscriber(PAYMENTS_NEW_QUEUE, PAYMENTS_EXCHANGE)
async def handle_payment_created(
    event: PaymentCreatedEvent,
    msg: RabbitMessage,
    logger: Logger,
) -> None:
    retry_count = int((msg.headers or {}).get("x-retry-count", 0))
    attempt = retry_count + 1
    logger.info(
        "Processing payment %s (attempt %s/%s)",
        event.payment_id,
        attempt,
        settings.consumer_max_attempts,
    )

    try:
        async with SessionLocal() as session:
            payment = await process_payment(session, event.payment_id)
        await send_webhook(payment)
    except Exception as exc:
        logger.warning(
            "Payment %s processing failed on attempt %s/%s: %s",
            event.payment_id,
            attempt,
            settings.consumer_max_attempts,
            exc,
        )
        if should_dead_letter(retry_count, settings.consumer_max_attempts):
            logger.error(
                "Payment %s exceeded %s attempts, sending to DLQ",
                event.payment_id,
                settings.consumer_max_attempts,
            )
            raise RejectMessage() from None

        await broker.publish(
            event,
            exchange=PAYMENTS_EXCHANGE,
            routing_key=retry_routing_key(retry_count),
            persist=True,
            message_id=str(event.payment_id),
            headers={"x-retry-count": retry_count + 1},
        )
        raise AckMessage() from None

    logger.info("Payment %s processed with status %s", event.payment_id, payment.status.value)


if __name__ == "__main__":
    import asyncio

    asyncio.run(app.run())
