from faststream import FastStream, Header

from app.broker.rabbit import broker, payments_new_queue, payments_exchange
from app.consumer.handlers import handle_payment_created

@broker.subscriber(
    queue=payments_new_queue,
    exchange=payments_exchange,
)
async def process_payment(
    message: dict,
    retry_count: int = Header(default=0)) -> None:
    await handle_payment_created(message, retry_count)
    

app = FastStream(broker)