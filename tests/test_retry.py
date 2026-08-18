from app.broker.topology import retry_routing_key, should_dead_letter


def test_retry_uses_exponential_delay_queues() -> None:
    assert retry_routing_key(0) == "payments.retry.1"
    assert retry_routing_key(1) == "payments.retry.2"
    assert retry_routing_key(2) == "payments.retry.3"


def test_message_goes_to_dlq_after_three_attempts() -> None:
    assert should_dead_letter(0, max_attempts=3) is False
    assert should_dead_letter(1, max_attempts=3) is False
    assert should_dead_letter(2, max_attempts=3) is True
