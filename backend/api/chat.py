import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import get_chat_extension, get_current_user_email
from extensions.chat import SecureChatExtension, ChatSession, Message, SecurityLevel

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Models ---

class CreateSessionRequest(BaseModel):
    peer_id: str
    security_level: int = 2

class SendMessageRequest(BaseModel):
    content: str  # Plaintext content from client
    security_level: int = 2

class SessionResponse(BaseModel):
    id: str
    peer_id: str
    security_level: int
    created_at: str
    is_active: bool

class MessageResponse(BaseModel):
    id: str
    sender: str
    recipient: str
    content: str  # Decrypted content
    timestamp: str
    security_level: int
    is_self: bool

# --- Endpoints ---

@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    chat_ext: SecureChatExtension = Depends(get_chat_extension),
    current_user: str = Depends(get_current_user_email)
):
    sessions = chat_ext.list_active_sessions()
    return [
        SessionResponse(
            id=s.id,
            peer_id=s.peer_id,
            security_level=s.security_level.value,
            created_at=s.created_at.isoformat(),
            is_active=s.is_active
        )
        for s in sessions
    ]

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    chat_ext: SecureChatExtension = Depends(get_chat_extension),
    current_user: str = Depends(get_current_user_email)
):
    try:
        level = SecurityLevel(request.security_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid security level")

    session = chat_ext.create_session(request.peer_id, level)
    return SessionResponse(
        id=session.id,
        peer_id=session.peer_id,
        security_level=session.security_level.value,
        created_at=session.created_at.isoformat(),
        is_active=session.is_active
    )

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    chat_ext: SecureChatExtension = Depends(get_chat_extension),
):
    session = chat_ext.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return SessionResponse(
        id=session.id,
        peer_id=session.peer_id,
        security_level=session.security_level.value,
        created_at=session.created_at.isoformat(),
        is_active=session.is_active
    )

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: str,
    chat_ext: SecureChatExtension = Depends(get_chat_extension),
    current_user: str = Depends(get_current_user_email)
):
    session = chat_ext.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response_messages = []
    for msg in session.messages:
        # In a real app, 'msg' would be encrypted. 
        # Here we assume the extension stores them as 'Message' objects (decrypted view)
        # because extensions/chat.py ChatSession.messages is List[Message].
        
        response_messages.append(MessageResponse(
            id=msg.id,
            sender=msg.sender,
            recipient=msg.recipient,
            content=msg.content.decode("utf-8"),
            timestamp=msg.timestamp.isoformat(),
            security_level=msg.security_level.value,
            is_self=(msg.sender == "self")
        ))
        
    return response_messages

@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    chat_ext: SecureChatExtension = Depends(get_chat_extension),
    current_user: str = Depends(get_current_user_email)
):
    session = chat_ext.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        level = SecurityLevel(request.security_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid security level")

    # 1. Encrypt content
    from qkd_client import KeyRequestError, KeyExhaustedError
    
    try:
        encrypted_msg = await chat_ext.encrypt_message(
            content=request.content.encode("utf-8"),
            recipient=session.peer_id,
            security_level=level
        )
    except KeyExhaustedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Insufficient key material: {str(e)}"
        )
    except KeyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Key Manager error: {str(e)}"
        )
    
    # 2. "Send" it (simulated by adding to queue/session immediately in this demo)
    # In reality, this would go to a transport layer.
    # For now, we decrypt it back to store in the 'sent' view of the session
    
    decrypted_msg_view = await chat_ext.decrypt_message(encrypted_msg)
    session.add_message(decrypted_msg_view)
    
    return MessageResponse(
        id=decrypted_msg_view.id,
        sender=decrypted_msg_view.sender,
        recipient=decrypted_msg_view.recipient,
        content=decrypted_msg_view.content.decode("utf-8"),
        timestamp=decrypted_msg_view.timestamp.isoformat(),
        security_level=decrypted_msg_view.security_level.value,
        is_self=True
    )
