import logging

import httpx

from app.config import settings
from app.models.payment import Payment

logger = logging.getLogger(__name__)


class WebhookDeliveryError(Exception):
    pass


async def send_webhook(payment: Payment) -> None:
    payload = {
        "payment_id": str(payment.id),
        "status": payment.status.value,
        "amount": str(payment.amount),
        "currency": payment.currency.value,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
            response = await client.post(payment.webhook_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Webhook delivery failed for payment %s: %s", payment.id, exc)
        raise WebhookDeliveryError(str(exc)) from exc

    logger.info("Webhook delivered for payment %s", payment.id)
