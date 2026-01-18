import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

_manager: Optional["AccountManager"] = None


@dataclass
class EmailAccount:
    id: str
    email: str
    provider: str = "gmail"
    display_name: Optional[str] = None
    is_active: bool = False
    connected_at: Optional[datetime] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class AccountManager:
    
    def __init__(self):
        self._accounts: Dict[str, EmailAccount] = {}
        self._active_account_id: Optional[str] = None
    
    def list_accounts(self) -> List[EmailAccount]:
        return list(self._accounts.values())
    
    def get_account(self, account_id: str) -> Optional[EmailAccount]:
        return self._accounts.get(account_id)
    
    def get_active_account(self) -> Optional[EmailAccount]:
        if self._active_account_id:
            return self._accounts.get(self._active_account_id)
        return None
    
    async def add_account(
        self,
        email: str,
        provider: str = "gmail",
        display_name: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> EmailAccount:
        account_id = str(uuid4())
        
        account = EmailAccount(
            id=account_id,
            email=email,
            provider=provider,
            display_name=display_name or email,
            is_active=len(self._accounts) == 0,
            connected_at=datetime.now(timezone.utc),
            access_token=access_token,
            refresh_token=refresh_token,
        )
        
        self._accounts[account_id] = account
        
        if account.is_active:
            self._active_account_id = account_id
        
        logger.info("Added account: %s (%s)", email, provider)
        return account
    
    async def set_active_account(self, account_id: str) -> bool:
        if account_id not in self._accounts:
            return False
        
        for acc in self._accounts.values():
            acc.is_active = False
        
        self._accounts[account_id].is_active = True
        self._active_account_id = account_id
        
        logger.info("Set active account: %s", self._accounts[account_id].email)
        return True
    
    async def remove_account(self, account_id: str) -> bool:
        if account_id not in self._accounts:
            return False
        
        email = self._accounts[account_id].email
        del self._accounts[account_id]
        
        if self._active_account_id == account_id:
            self._active_account_id = None
            if self._accounts:
                first_id = next(iter(self._accounts))
                self._accounts[first_id].is_active = True
                self._active_account_id = first_id
        
        logger.info("Removed account: %s", email)
        return True
    
    async def update_tokens(
        self,
        account_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> bool:
        account = self._accounts.get(account_id)
        if not account:
            return False
        
        account.access_token = access_token
        if refresh_token:
            account.refresh_token = refresh_token
        
        return True
    
    def get_account_by_email(self, email: str) -> Optional[EmailAccount]:
        for account in self._accounts.values():
            if account.email == email:
                return account
        return None


async def get_account_manager() -> AccountManager:
    global _manager
    if _manager is None:
        _manager = AccountManager()
    return _manager
