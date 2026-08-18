from decimal import Decimal

from app.enums import Currency
from app.models.payment import Payment
from app.schemas.payment import PaymentCreateRequest


def payloads_match(payment: Payment, data: PaymentCreateRequest) -> bool:
    return (
        payment.amount == Decimal(data.amount)
        and payment.currency == Currency(data.currency)
        and payment.description == data.description
        and payment.extra_data == data.metadata
        and payment.webhook_url == str(data.webhook_url)
    )
