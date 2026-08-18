from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IdempotencyConflictError, PaymentNotFoundError
from app.enums import PaymentStatus
from app.models.outbox import OutboxEvent
from app.models.payment import Payment
from app.schemas.events import PaymentCreatedEvent
from app.schemas.payment import PaymentCreateRequest
from app.services.idempotency import payloads_match


async def create_payment(
    session: AsyncSession,
    data: PaymentCreateRequest,
    idempotency_key: str,
) -> Payment:
    existing = await _get_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        if not payloads_match(existing, data):
            raise IdempotencyConflictError
        return existing

    payment_id = uuid4()
    payment = Payment(
        id=payment_id,
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        extra_data=data.metadata,
        status=PaymentStatus.PENDING,
        idempotency_key=idempotency_key,
        webhook_url=str(data.webhook_url),
    )
    event = OutboxEvent(
        event_type="payment.created",
        payload=PaymentCreatedEvent(payment_id=payment_id).model_dump(mode="json"),
    )
    session.add_all([payment, event])

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await _get_by_idempotency_key(session, idempotency_key)
        if existing is None:
            raise
        if not payloads_match(existing, data):
            raise IdempotencyConflictError from None
        return existing

    await session.refresh(payment)
    return payment


async def get_payment(session: AsyncSession, payment_id: UUID) -> Payment:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise PaymentNotFoundError(str(payment_id))
    return payment


async def _get_by_idempotency_key(
    session: AsyncSession,
    idempotency_key: str,
) -> Payment | None:
    stmt = select(Payment).where(Payment.idempotency_key == idempotency_key)
    return await session.scalar(stmt)
