from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import respx

from app.enums import Currency, PaymentStatus
from app.services.webhook import WebhookDeliveryError, send_webhook


def _payment() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        amount=Decimal("99.10"),
        currency=Currency.RUB,
        status=PaymentStatus.SUCCEEDED,
        webhook_url="https://hooks.example.com/payments",
        processed_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_send_webhook_success() -> None:
    payment = _payment()

    with respx.mock(assert_all_called=True) as router:
        route = router.post(payment.webhook_url).mock(return_value=httpx.Response(200))
        await send_webhook(payment)
        assert route.called
        assert str(payment.id).encode() in route.calls.last.request.content


@pytest.mark.asyncio
async def test_send_webhook_raises_on_http_error() -> None:
    payment = _payment()

    with respx.mock(assert_all_called=True) as router:
        router.post(payment.webhook_url).mock(return_value=httpx.Response(500))
        with pytest.raises(WebhookDeliveryError):
            await send_webhook(payment)
        assert router.calls.call_count == 1
