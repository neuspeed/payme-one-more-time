import asyncio
import random

class PaymentGatewayError(Exception):
    pass

async def process_payment_via_gateway(payment_id: str) -> bool:
    await asyncio.sleep(random.uniform(2, 5))
    if random.random() < 0.9:
        return True
    raise PaymentGatewayError("gateway declined")