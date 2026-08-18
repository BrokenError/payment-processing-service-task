from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.enums import Currency, PaymentStatus
from app.services import processor as processor_module


def _payment(status: PaymentStatus) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        amount=Decimal("10.00"),
        currency=Currency.EUR,
        description="desc",
        extra_data={},
        status=status,
        webhook_url="https://example.com/hook",
        created_at=datetime.now(UTC),
        processed_at=None,
    )


@pytest.mark.asyncio
async def test_process_payment_skips_already_finished() -> None:
    payment = _payment(PaymentStatus.SUCCEEDED)
    session = AsyncMock()
    session.get = AsyncMock(return_value=payment)

    result = await processor_module.process_payment(session, payment.id)

    assert result is payment
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_process_payment_marks_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment = _payment(PaymentStatus.PENDING)
    session = AsyncMock()
    session.get = AsyncMock(return_value=payment)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(processor_module.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(processor_module.random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(processor_module.random, "random", lambda: 0.01)

    result = await processor_module.process_payment(session, payment.id)

    assert result.status == PaymentStatus.SUCCEEDED
    assert result.processed_at is not None
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_process_payment_marks_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment = _payment(PaymentStatus.PENDING)
    session = AsyncMock()
    session.get = AsyncMock(return_value=payment)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(processor_module.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(processor_module.random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(processor_module.random, "random", lambda: 0.99)

    result = await processor_module.process_payment(session, payment.id)

    assert result.status == PaymentStatus.FAILED
    session.commit.assert_awaited()
