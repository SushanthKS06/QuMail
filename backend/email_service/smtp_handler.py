import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from typing import List, Optional
from uuid import uuid4

import aiosmtplib

from config import settings
from .oauth2 import get_valid_token
from .mime_builder import build_encrypted_mime

logger = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


async def send_email(
    to: List[str],
    cc: List[str],
    subject: str,
    body: str,
    security_level: int,
    key_id: Optional[str] = None,
    attachments: Optional[List[dict]] = None,
) -> str:
    from storage.database import get_stored_accounts
    
    accounts = await get_stored_accounts()
    if not accounts:
        raise ValueError("No email account configured. Please authenticate with Gmail.")
    
    account = accounts[0]
    from_email = account["email"]
    
    access_token = await get_valid_token(from_email)
    
    if security_level < 4:
        message = build_encrypted_mime(
            from_addr=from_email,
            to_addrs=to,
            cc_addrs=cc,
            subject=subject,
            encrypted_body=body,
            security_level=security_level,
            key_id=key_id,
            attachments=attachments,
        )
    else:
        message = MIMEMultipart()
        message["From"] = from_email
        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "plain", "utf-8"))
        
        if attachments:
            for att in attachments:
                part = MIMEApplication(att["content"], Name=att["filename"])
                part["Content-Disposition"] = f'attachment; filename="{att["filename"]}"'
                message.attach(part)
    
    message_id = f"<{uuid4()}@qumail.local>"
    message["Message-ID"] = message_id
    
    all_recipients = to + cc
    
    try:
        smtp = aiosmtplib.SMTP(
            hostname=GMAIL_SMTP_HOST,
            port=GMAIL_SMTP_PORT,
            start_tls=True,
        )
        
        await smtp.connect()
        
        await smtp.auth_plain(from_email, access_token)
        
        await smtp.send_message(message, recipients=all_recipients)
        
        await smtp.quit()
        
        logger.info(
            "Email sent: %s, to=%s, security_level=%d",
            message_id, to, security_level
        )
        
        from storage.database import save_sent_email
        await save_sent_email(
            message_id=message_id,
            from_addr=from_email,
            to_addrs=to,
            cc_addrs=cc,
            subject=subject,
            body=body,
            security_level=security_level,
            key_id=key_id,
        )
        
        return message_id
        
    except aiosmtplib.SMTPAuthenticationError as e:
        logger.error("SMTP authentication failed: %s", e)
        raise ValueError("Email authentication failed. Please re-authenticate.")
    except Exception as e:
        logger.exception("Failed to send email: %s", e)
        raise


async def send_email_raw(
    from_email: str,
    to_emails: List[str],
    raw_message: bytes,
    access_token: str,
) -> str:
    smtp = aiosmtplib.SMTP(
        hostname=GMAIL_SMTP_HOST,
        port=GMAIL_SMTP_PORT,
        start_tls=True,
    )
    
    await smtp.connect()
    await smtp.auth_plain(from_email, access_token)
    
    result = await smtp.sendmail(from_email, to_emails, raw_message)
    
    await smtp.quit()
    
    return "sent"
