import httpx
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("webhook_sender")

class WebhookError(Exception):
    pass

class PermanentWebhookError(Exception):
    pass

async def send_webhook(url: str, payload: dict) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        logger.info("POST webhook url=%s payload=%s", url, payload)
        try:
            response = await client.post(url, json=payload)
        except httpx.RequestError as e:
            logger.warning("webhook network error: %s", e)
            raise WebhookError(str(e)) from e

        logger.info("webhook response status=%s body=%s",
                    response.status_code, response.text[:200])

        if response.status_code >= 500:
            raise WebhookError(f"server error: {response.status_code}")
        if 400 <= response.status_code < 500:
            raise PermanentWebhookError(f"client error: {response.status_code}")