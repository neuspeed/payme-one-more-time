import os

from faststream.rabbit import (
    ExchangeType,
    RabbitBroker,
    RabbitExchange,
    RabbitQueue
)

RABBITMQ_URL = os.getenv("RABBITMQ_URL")

broker = RabbitBroker(
    url=RABBITMQ_URL
)

payments_exchange = RabbitExchange(
    "payments.exchange",
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_dlx = RabbitExchange(
    "payments.dlx",
    type=ExchangeType.DIRECT,
    durable=True
)

payments_new_queue = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-dead-letter-exchange": payments_dlx.name,
        "x-dead-letter-routing-key": "payments.new.dlq",
    }
)

def _retry_queue(name: str, ttl_ms: int, routing_key: str) -> RabbitQueue:
    return RabbitQueue(
        name,
        durable=True,
        routing_key=routing_key,
        arguments={
            "x-message-ttl": ttl_ms,
            "x-dead-letter-exchange": payments_exchange.name,
            "x-dead-letter-routing-key": "payments.new"
        }
    )
    

retry_5s = _retry_queue("payments.new_retry.5s", 5_000, "payments.new.retry.5s")
retry_25s = _retry_queue("payments.new_retry.25s", 25_000, "payments.new.retry.25s")
retry_125s = _retry_queue("payments.new_retry.125s", 125_000, "payments.new.retry.125s")

payments_dlq = RabbitQueue(
    "payments.new.dlq",
    durable=True,
    routing_key="payments.new.dlq",
)

RETRY_QUEUES = [retry_5s, retry_25s, retry_125s] 

MAX_RETRIES = len(RETRY_QUEUES)