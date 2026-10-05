import os
import secrets
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("API_KEY", "dev-secret-key")  # лучше брать из ENV

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key is None or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key