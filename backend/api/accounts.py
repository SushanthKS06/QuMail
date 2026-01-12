import logging
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.dependencies import TokenDep
from accounts import get_account_manager, EmailAccount

logger = logging.getLogger(__name__)
router = APIRouter()


class AccountSummary(BaseModel):
    id: str
    email: str
    provider: str
    display_name: str | None
    is_active: bool
    connected_at: str | None


class AccountListResponse(BaseModel):
    accounts: List[AccountSummary]
    active_account_id: str | None


class SetActiveRequest(BaseModel):
    account_id: str


@router.get("", response_model=AccountListResponse)
async def list_accounts(token: TokenDep):
    manager = await get_account_manager()
    
    accounts = manager.list_accounts()
    active = manager.get_active_account()
    
    return AccountListResponse(
        accounts=[
            AccountSummary(
                id=acc.id,
                email=acc.email,
                provider=acc.provider,
                display_name=acc.display_name,
                is_active=acc.is_active,
                connected_at=acc.connected_at.isoformat() if acc.connected_at else None,
            )
            for acc in accounts
        ],
        active_account_id=active.id if active else None,
    )


@router.post("/active")
async def set_active_account(token: TokenDep, request: SetActiveRequest):
    manager = await get_account_manager()
    
    success = await manager.set_active_account(request.account_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {request.account_id}",
        )
    
    return {"success": True, "active_account_id": request.account_id}


@router.delete("/{account_id}")
async def remove_account(token: TokenDep, account_id: str):
    manager = await get_account_manager()
    
    success = await manager.remove_account(account_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )
    
    return {"success": True, "removed_account_id": account_id}


@router.get("/active")
async def get_active_account(token: TokenDep):
    manager = await get_account_manager()
    
    account = manager.get_active_account()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active account configured",
        )
    
    return AccountSummary(
        id=account.id,
        email=account.email,
        provider=account.provider,
        display_name=account.display_name,
        is_active=account.is_active,
        connected_at=account.connected_at.isoformat() if account.connected_at else None,
    )
