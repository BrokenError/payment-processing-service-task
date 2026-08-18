from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.config import settings

PAYMENTS_EXCHANGE_NAME = "payments"
PAYMENTS_DLX_NAME = "payments.dlx"
PAYMENTS_NEW_QUEUE_NAME = "payments.new"
PAYMENTS_DLQ_NAME = "payments.new.dlq"
PAYMENTS_NEW_ROUTING_KEY = "payments.new"

RETRY_DELAYS_MS = (2_000, 4_000, 8_000)

PAYMENTS_EXCHANGE = RabbitExchange(
    PAYMENTS_EXCHANGE_NAME,
    durable=True,
    type=ExchangeType.DIRECT,
)
PAYMENTS_DLX = RabbitExchange(
    PAYMENTS_DLX_NAME,
    durable=True,
    type=ExchangeType.DIRECT,
)

PAYMENTS_NEW_QUEUE = RabbitQueue(
    PAYMENTS_NEW_QUEUE_NAME,
    durable=True,
    routing_key=PAYMENTS_NEW_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_DLX_NAME,
        "x-dead-letter-routing-key": PAYMENTS_NEW_ROUTING_KEY,
    },
)

PAYMENTS_DLQ = RabbitQueue(
    PAYMENTS_DLQ_NAME,
    durable=True,
    routing_key=PAYMENTS_NEW_ROUTING_KEY,
)

RETRY_QUEUES = tuple(
    RabbitQueue(
        f"payments.retry.{attempt}",
        durable=True,
        routing_key=f"payments.retry.{attempt}",
        arguments={
            "x-message-ttl": delay_ms,
            "x-dead-letter-exchange": PAYMENTS_EXCHANGE_NAME,
            "x-dead-letter-routing-key": PAYMENTS_NEW_ROUTING_KEY,
        },
    )
    for attempt, delay_ms in enumerate(RETRY_DELAYS_MS, start=1)
)


def create_broker() -> RabbitBroker:
    return RabbitBroker(settings.rabbitmq_url, max_consumers=1)


async def declare_topology(broker: RabbitBroker) -> None:
    exchange = await broker.declare_exchange(PAYMENTS_EXCHANGE)
    dlx = await broker.declare_exchange(PAYMENTS_DLX)

    new_queue = await broker.declare_queue(PAYMENTS_NEW_QUEUE)
    await new_queue.bind(exchange, routing_key=PAYMENTS_NEW_ROUTING_KEY)

    dlq = await broker.declare_queue(PAYMENTS_DLQ)
    await dlq.bind(dlx, routing_key=PAYMENTS_NEW_ROUTING_KEY)

    for retry_queue in RETRY_QUEUES:
        declared = await broker.declare_queue(retry_queue)
        await declared.bind(exchange, routing_key=retry_queue.routing_key or retry_queue.name)


def retry_routing_key(retry_count: int) -> str:
    return f"payments.retry.{retry_count + 1}"


def should_dead_letter(retry_count: int, max_attempts: int) -> bool:
    return retry_count + 1 >= max_attempts
