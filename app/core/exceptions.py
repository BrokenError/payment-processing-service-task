class DomainError(Exception):
    pass


class PaymentNotFoundError(DomainError):
    def __init__(self, payment_id: str) -> None:
        super().__init__(f"Payment {payment_id} not found")
        self.payment_id = payment_id


class IdempotencyConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Idempotency-Key was already used with a different payment payload"
        )
