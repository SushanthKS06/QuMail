import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.dependencies import TokenDep
from storage.database import get_settings, save_setting

logger = logging.getLogger(__name__)
router = APIRouter()


class SettingsUpdate(BaseModel):
    theme: str
    security_level: int


@router.get("", response_model=Dict[str, Any])
async def get_settings_endpoint(token: TokenDep):
    try:
        return await get_settings()
    except Exception as e:
        logger.exception("Failed to fetch settings: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("", response_model=Dict[str, Any])
async def update_settings_endpoint(token: TokenDep, settings: SettingsUpdate):
    try:
        await save_setting("theme", settings.theme)
        await save_setting("security_level", settings.security_level)
        
        return await get_settings()
    except Exception as e:
        logger.exception("Failed to update settings: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
