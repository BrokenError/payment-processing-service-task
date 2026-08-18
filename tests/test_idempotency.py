from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.enums import Currency, PaymentStatus
from app.schemas.payment import PaymentCreateRequest
from app.services.idempotency import payloads_match


def _payment(**overrides: object) -> SimpleNamespace:
    data = {
        "id": uuid4(),
        "amount": Decimal("10.00"),
        "currency": Currency.USD,
        "description": "Order 1",
        "extra_data": {"a": 1},
        "status": PaymentStatus.PENDING,
        "webhook_url": "https://example.com/hook",
        "created_at": datetime.now(UTC),
        "processed_at": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_payloads_match_for_identical_request() -> None:
    payment = _payment()
    request = PaymentCreateRequest(
        amount=Decimal("10.00"),
        currency=Currency.USD,
        description="Order 1",
        metadata={"a": 1},
        webhook_url="https://example.com/hook",
    )

    assert payloads_match(payment, request) is True


def test_payloads_do_not_match_when_amount_differs() -> None:
    payment = _payment()
    request = PaymentCreateRequest(
        amount=Decimal("11.00"),
        currency=Currency.USD,
        description="Order 1",
        metadata={"a": 1},
        webhook_url="https://example.com/hook",
    )

    assert payloads_match(payment, request) is False
