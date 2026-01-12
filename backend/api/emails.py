"""
Email API Routes

Handles email sending, receiving, and management.
All encryption/decryption happens transparently in the backend.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, EmailStr, Field

from api.dependencies import TokenDep
from crypto_engine import encrypt_email, decrypt_email
from email_service import send_email, fetch_emails, get_email_by_id
from policy_engine import validate_send_request, check_recipient_capability
from qkd_client import request_key, KeyRequestError

logger = logging.getLogger(__name__)
router = APIRouter()


class AttachmentMeta(BaseModel):
    """Attachment metadata."""
    filename: str
    size: int
    content_type: str


class EmailSummary(BaseModel):
    """Email summary for listing."""
    message_id: str
    from_address: str = Field(alias="from")
    to: List[str]
    subject: str
    preview: str
    received_at: datetime
    security_level: int
    has_attachments: bool
    is_read: bool


class EmailDetail(BaseModel):
    """Full email detail."""
    message_id: str
    from_address: str = Field(alias="from")
    to: List[str]
    cc: List[str] = []
    subject: str
    body: str
    html_body: Optional[str] = None
    attachments: List[AttachmentMeta] = []
    received_at: datetime
    security_level: int
    key_id: Optional[str] = None
    decryption_status: str = "success"


class SendEmailRequest(BaseModel):
    """Request to send an email."""
    to: List[EmailStr]
    cc: List[EmailStr] = []
    subject: str
    body: str
    security_level: int = Field(default=2, ge=1, le=4)
    attachments: List[str] = []


class SendEmailResponse(BaseModel):
    """Response after sending email."""
    success: bool
    message_id: Optional[str] = None
    key_id: Optional[str] = None
    security_level_used: int
    error: Optional[str] = None


class EmailListResponse(BaseModel):
    """Response for email list."""
    emails: List[EmailSummary]
    total: int
    has_more: bool


class DraftRequest(BaseModel):
    """Request to save draft."""
    to: List[str] = []
    cc: List[str] = []
    subject: str = ""
    body: str = ""
    security_level: int = 2


class DraftResponse(BaseModel):
    """Response after saving draft."""
    draft_id: str
    saved_at: datetime


@router.get("", response_model=EmailListResponse)
async def list_emails(
    token: TokenDep,
    folder: str = Query(default="INBOX"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    decrypt: bool = Query(default=True),
):
    """
    Fetch emails from the specified folder.
    
    Encrypted emails are automatically decrypted if decrypt=True.
    The security_level field indicates the encryption used.
    """
    try:
        offset = (page - 1) * limit
        
        emails, total = await fetch_emails(
            folder=folder,
            offset=offset,
            limit=limit,
        )
        
        email_summaries = []
        for email in emails:
            if decrypt and email.get("encrypted"):
                try:
                    decrypted = await decrypt_email(email)
                    email.update(decrypted)
                except Exception as e:
                    logger.warning("Failed to decrypt email %s: %s", email["message_id"], e)
                    email["preview"] = "[Encrypted - Unable to decrypt]"
            
            email_summaries.append(EmailSummary(
                message_id=email["message_id"],
                **{"from": email["from"]},
                to=email["to"],
                subject=email.get("subject", "(No Subject)"),
                preview=email.get("preview", "")[:200],
                received_at=email["received_at"],
                security_level=email.get("security_level", 4),
                has_attachments=len(email.get("attachments", [])) > 0,
                is_read=email.get("is_read", False),
            ))
        
        return EmailListResponse(
            emails=email_summaries,
            total=total,
            has_more=(offset + limit) < total,
        )
        
    except Exception as e:
        logger.exception("Failed to fetch emails: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{message_id}", response_model=EmailDetail)
async def get_email(token: TokenDep, message_id: str):
    """
    Get full email content by message ID.
    
    Automatically decrypts the email body and attachments.
    """
    try:
        email = await get_email_by_id(message_id)
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found",
            )
        
        decryption_status = "success"
        if email.get("encrypted"):
            try:
                decrypted = await decrypt_email(email)
                email.update(decrypted)
            except Exception as e:
                logger.warning("Decryption failed for %s: %s", message_id, e)
                email["body"] = "[Encrypted - Unable to decrypt]"
                decryption_status = f"failed: {str(e)}"
        
        return EmailDetail(
            message_id=email["message_id"],
            **{"from": email["from"]},
            to=email["to"],
            cc=email.get("cc", []),
            subject=email.get("subject", "(No Subject)"),
            body=email.get("body", ""),
            html_body=email.get("html_body"),
            attachments=[
                AttachmentMeta(
                    filename=att["filename"],
                    size=att["size"],
                    content_type=att["content_type"],
                )
                for att in email.get("attachments", [])
            ],
            received_at=email["received_at"],
            security_level=email.get("security_level", 4),
            key_id=email.get("key_id"),
            decryption_status=decryption_status,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get email: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/send", response_model=SendEmailResponse)
async def send_email_endpoint(
    token: TokenDep,
    request: SendEmailRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send an encrypted email.
    
    Security Levels:
    - 1: One-Time Pad (requires sufficient QKD key material)
    - 2: Quantum-Aided AES-256-GCM (default)
    - 3: Post-Quantum Crypto (Kyber + Dilithium)
    - 4: Plain text (no encryption)
    """
    try:
        validation = await validate_send_request(
            recipients=request.to + request.cc,
            security_level=request.security_level,
            body_size=len(request.body.encode()),
        )
        
        if not validation["valid"]:
            return SendEmailResponse(
                success=False,
                security_level_used=request.security_level,
                error=validation["error"],
            )
        
        actual_level = validation.get("adjusted_level", request.security_level)
        
        if actual_level == 4:
            encrypted_body = request.body
            key_id = None
        else:
            encrypted_result = await encrypt_email(
                body=request.body,
                security_level=actual_level,
                recipients=request.to,
            )
            encrypted_body = encrypted_result["ciphertext"]
            key_id = encrypted_result.get("key_id")
        
        message_id = await send_email(
            to=request.to,
            cc=request.cc,
            subject=request.subject,
            body=encrypted_body,
            security_level=actual_level,
            key_id=key_id,
        )
        
        logger.info(
            "Email sent: %s, security_level=%d, key_id=%s",
            message_id, actual_level, key_id
        )
        
        return SendEmailResponse(
            success=True,
            message_id=message_id,
            key_id=key_id,
            security_level_used=actual_level,
        )
        
    except KeyRequestError as e:
        logger.error("Key request failed: %s", e)
        return SendEmailResponse(
            success=False,
            security_level_used=request.security_level,
            error=f"Insufficient key material: {e}",
        )
    except Exception as e:
        logger.exception("Failed to send email: %s", e)
        return SendEmailResponse(
            success=False,
            security_level_used=request.security_level,
            error=str(e),
        )


@router.post("/draft", response_model=DraftResponse)
async def save_draft(token: TokenDep, request: DraftRequest):
    """Save email as draft."""
    from storage.database import save_email_draft
    
    draft_id = str(uuid4())
    saved_at = datetime.utcnow()
    
    await save_email_draft(
        draft_id=draft_id,
        to=request.to,
        cc=request.cc,
        subject=request.subject,
        body=request.body,
        security_level=request.security_level,
    )
    
    return DraftResponse(draft_id=draft_id, saved_at=saved_at)


@router.delete("/{message_id}")
async def delete_email(token: TokenDep, message_id: str):
    """Delete an email."""
    from email_service import delete_email as do_delete
    
    try:
        await do_delete(message_id)
        return {"success": True, "message_id": message_id}
    except Exception as e:
        logger.exception("Failed to delete email: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{message_id}/attachment/{attachment_id}")
async def get_attachment(token: TokenDep, message_id: str, attachment_id: str):
    """Download and decrypt an attachment."""
    from email_service import get_attachment_content
    from crypto_engine import decrypt_attachment
    
    try:
        email = await get_email_by_id(message_id)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        attachment = await get_attachment_content(message_id, attachment_id)
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        if email.get("encrypted") and email.get("security_level", 4) < 4:
            decrypted = await decrypt_attachment(
                attachment["content"],
                email.get("key_id"),
                email.get("security_level"),
            )
            attachment["content"] = decrypted
        
        from fastapi.responses import Response
        return Response(
            content=attachment["content"],
            media_type=attachment["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{attachment["filename"]}"'
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get attachment: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
