import os
import asyncio
import logging

from datetime import datetime, timezone
from sqlalchemy import select
from dotenv import load_dotenv

from app.core.database import AsyncSessionLocal
from app.models.outbox import Outbox, OutboxStatus
from app.broker.rabbit import broker, payments_exchange

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("publisher")

load_dotenv()

POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))


async def run_outbox_publisher(): 
    logger.info("outbox publisher started")
    while True:
        try:
            count = await publish_pending_batch()
            logger.info(f"outbox batch processed: {count}")
        except Exception as e:
            logger.exception(f"outbox publisher error: {e}")
        await asyncio.sleep(POLL_INTERVAL) 
        

async def publish_pending_batch():
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Outbox)
            .where(Outbox.status == OutboxStatus.pending)
            .order_by(Outbox.occurred_at)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
        events = (await db.scalars(stmt)).all()
        if not events:
            return
        
        for event in events:
            try:
                await broker.publish(
                    event.payload,
                    exchange=payments_exchange,
                    routing_key="payments.new",
                    headers={
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
                        "retry_count": 0,
                    },
                    persist=True,
                    mandatory=True,
                )
            except Exception as e:
                logger.exception(
                    f"Failed to publish event {event.event_id}, will retry next iteration"
                )
                continue
            event.status = OutboxStatus.published
            event.sent_at = datetime.now(timezone.utc)
            
            await db.commit()