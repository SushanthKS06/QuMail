import logging
from typing import Annotated

import httpx
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from config import settings

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=settings.km_timeout)
    return _http_client


async def verify_api_token(
    authorization: Annotated[str | None, Header()] = None
) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        return payload.get("sub", "frontend")
    except JWTError as e:
        logger.warning("Invalid token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


TokenDep = Annotated[str, Depends(verify_api_token)]


async def verify_startup_requirements() -> None:
    client = await get_http_client()
    
    try:
        response = await client.get(f"{settings.km_url}/health")
        if response.status_code != 200:
            logger.warning("Key Manager health check failed: %s", response.status_code)
        else:
            logger.info("Key Manager connection verified")
    except httpx.ConnectError:
        logger.warning(
            "Key Manager not reachable at %s - some features will be unavailable",
            settings.km_url,
        )
    except Exception as e:
        logger.warning("Key Manager check failed: %s", e)
