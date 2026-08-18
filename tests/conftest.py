import os
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://payments:payments@localhost:5432/payments",
)
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

from app.db.session import get_session  # noqa: E402
from app.enums import Currency, PaymentStatus  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def api_headers() -> dict[str, str]:
    return {
        "X-API-Key": "test-api-key",
        "Idempotency-Key": str(uuid4()),
        "Content-Type": "application/json",
    }


@pytest.fixture
def sample_payment() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        amount=Decimal("150.50"),
        currency=Currency.RUB,
        description="Test payment",
        extra_data={"order_id": "42"},
        status=PaymentStatus.PENDING,
        idempotency_key="key-1",
        webhook_url="https://example.com/webhook",
        created_at=datetime.now(UTC),
        processed_at=None,
    )


@pytest.fixture
def client(sample_payment: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = create_app(enable_outbox=False)

    async def fake_create_payment(session, data, idempotency_key):  # noqa: ANN001, ARG001
        return sample_payment

    async def fake_get_payment(session, payment_id):  # noqa: ANN001, ARG001
        from app.core.exceptions import PaymentNotFoundError

        if str(payment_id) == str(sample_payment.id):
            return sample_payment
        raise PaymentNotFoundError(str(payment_id))

    monkeypatch.setattr("app.api.v1.payments.payment_service.create_payment", fake_create_payment)
    monkeypatch.setattr("app.api.v1.payments.payment_service.get_payment", fake_get_payment)

    async def override_session():  # noqa: ANN202
        yield object()

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as test_client:
        yield test_client
