import base64
import logging
from datetime import datetime, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)


def detect_provider(email: str) -> str:
    email_lower = email.lower()
    if "@yahoo" in email_lower or "@ymail" in email_lower:
        return "yahoo"
    elif "@gmail" in email_lower or "@googlemail" in email_lower:
        return "gmail"
    return "gmail"


async def get_valid_token(email: str, force_refresh: bool = False) -> str:
    from storage.database import get_oauth_tokens, store_oauth_tokens
    
    tokens = await get_oauth_tokens(email)
    
    if not tokens:
        raise ValueError(f"No OAuth tokens for {email}. Please authenticate.")
    
    provider = tokens.get("provider") or detect_provider(email)
    should_refresh = force_refresh
    
    if not should_refresh and tokens.get("expires_at"):
        expires_at = tokens["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        if datetime.now(timezone.utc) >= expires_at:
            logger.info("Access token expired for %s, refreshing...", email)
            should_refresh = True
            
    if should_refresh:
        logger.info("Refreshing OAuth token for %s (provider=%s, force=%s)", email, provider, force_refresh)
        new_tokens = await refresh_oauth_token(tokens["refresh_token"], provider)
        
        await store_oauth_tokens(
            email=email,
            access_token=new_tokens["access_token"],
            refresh_token=new_tokens.get("refresh_token", tokens["refresh_token"]),
            expires_in=new_tokens.get("expires_in", 3600),
            provider=provider,
        )
        
        return new_tokens["access_token"]
    
    return tokens["access_token"]


async def refresh_oauth_token(refresh_token: str, provider: str = "gmail") -> dict:
    if provider == "yahoo":
        return await _refresh_yahoo_token(refresh_token)
    else:
        return await _refresh_gmail_token(refresh_token)


async def _refresh_gmail_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        
        if response.status_code != 200:
            logger.error("Gmail token refresh failed: %s", response.text)
            raise ValueError("Failed to refresh Gmail OAuth token. Please re-authenticate.")
        
        return response.json()


async def _refresh_yahoo_token(refresh_token: str) -> dict:
    credentials = base64.b64encode(
        f"{settings.yahoo_client_id}:{settings.yahoo_client_secret}".encode()
    ).decode()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.login.yahoo.com/oauth2/get_token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        
        if response.status_code != 200:
            logger.error("Yahoo token refresh failed: %s", response.text)
            raise ValueError("Failed to refresh Yahoo OAuth token. Please re-authenticate.")
        
        return response.json()


async def revoke_oauth_token(token: str, provider: str = "gmail") -> bool:
    if provider == "yahoo":
        return True
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
        )
        
        return response.status_code == 200
