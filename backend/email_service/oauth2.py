import logging
from datetime import datetime, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def get_valid_token(email: str) -> str:
    from storage.database import get_oauth_tokens, store_oauth_tokens
    
    tokens = await get_oauth_tokens(email)
    
    if not tokens:
        raise ValueError(f"No OAuth tokens for {email}. Please authenticate.")
    
    if tokens.get("expires_at"):
        expires_at = tokens["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        if datetime.now(timezone.utc) >= expires_at:
            logger.info("Access token expired for %s, refreshing...", email)
            
            new_tokens = await refresh_oauth_token(tokens["refresh_token"])
            
            await store_oauth_tokens(
                email=email,
                access_token=new_tokens["access_token"],
                refresh_token=new_tokens.get("refresh_token", tokens["refresh_token"]),
                expires_in=new_tokens.get("expires_in", 3600),
            )
            
            return new_tokens["access_token"]
    
    return tokens["access_token"]


async def refresh_oauth_token(refresh_token: str) -> dict:
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
            logger.error("Token refresh failed: %s", response.text)
            raise ValueError("Failed to refresh OAuth token. Please re-authenticate.")
        
        return response.json()


async def revoke_oauth_token(token: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
        )
        
        return response.status_code == 200
