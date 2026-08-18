import asyncio
import random
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import PaymentNotFoundError
from app.enums import PaymentStatus
from app.models.payment import Payment


async def process_payment(session: AsyncSession, payment_id: UUID) -> Payment:
    payment = await session.get(Payment, payment_id, with_for_update=True)
    if payment is None:
        raise PaymentNotFoundError(str(payment_id))

    if payment.status != PaymentStatus.PENDING:
        return payment

    delay = random.uniform(
        settings.payment_process_min_seconds,
        settings.payment_process_max_seconds,
    )
    await asyncio.sleep(delay)

    succeeded = random.random() < settings.payment_success_rate
    payment.status = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
    payment.processed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(payment)
    return payment
