from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.broker.rabbit import (
    broker,
    payments_exchange,
    payments_dlx,
    RETRY_QUEUES,
    MAX_RETRIES
)

from app.consumer.gateway import PaymentGatewayError, process_payment_via_gateway
from app.consumer.webhook import WebhookError, PermanentWebhookError, send_webhook

from app.models.payment import Payment, PaymentStatus

class PermanentError(Exception):
    pass

class TransientError(Exception):
    pass


async def handle_payment_created(message: dict, retry_count: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await _process(message, db)
    except PermanentError as e:
        await _send_to_dlq(message, reason=str(e))
        return
    except (TransientError, PaymentGatewayError, WebhookError) as e:
        if retry_count < MAX_RETRIES:
            await _send_to_retry(message, retry_count)
        else:
            await _send_to_dlq(message, reason=str(e))
        return    
    
    
async def _process(message: dict, db: AsyncSession) -> None:
    payment_id = message.get("payment_id")
    payment = await db.get(Payment, int(payment_id))
    if payment is None:
        raise PermanentError(f"payment {payment_id} not found")
    
    if payment.status in (PaymentStatus.succeeded, PaymentStatus.failed):
        return
    
    try:
        success = await process_payment_via_gateway(payment_id)
        payment.status = PaymentStatus.succeeded if success else PaymentStatus.failed
    except PaymentGatewayError as e:
        payment.status = PaymentStatus.failed
        payment.updated_at = datetime.now(timezone.utc)
        await db.commit()
        raise TransientError(str(e))    
    
    payment.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    try:
        await send_webhook(
            url=payment.webhook_url,
            payload={
                "payment_id": str(payment.id),
                "status": payment.status.value,
                "amount": str(payment.amount),
                "currency": payment.currency,
            }
        )
    except PermanentWebhookError as e:
        raise PermanentError(str(e))
    except WebhookError as e:
        raise TransientError(str(e))
    
    
async def _send_to_retry(message, retry_count):
    next_queue = RETRY_QUEUES[retry_count]
    await broker.publish(
        message=message,
        exchange=payments_exchange,
        routing_key=next_queue.routing_key,
        headers={
            "retry_count": retry_count + 1
        },
        persist=True,
    )
    
async def _send_to_dlq(message, reason: str):
    await broker.publish(
        message=message,
        exchange=payments_dlx,
        routing_key="payments.new.dlq",
        headers={
            "error": reason
        },
        persist=True,
    )