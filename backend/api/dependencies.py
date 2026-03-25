from typing import Annotated, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from extensions.chat import SecureChatExtension, create_chat_extension

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    # Simulating token validation for the demo
    # In real app, verify_token(token) would be called
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "user@qumail.com"  # Mock user for now or decode token if secret available

TokenDep = Annotated[str, Depends(get_current_user_email)]



_chat_extension_instance = None

def get_chat_extension() -> SecureChatExtension:
    global _chat_extension_instance
    if _chat_extension_instance is None:
        _chat_extension_instance = create_chat_extension()
    return _chat_extension_instance

async def verify_startup_requirements():
    # ... existing logic ...
    # Initialize chat ext
    chat = get_chat_extension()
    await chat.initialize()
