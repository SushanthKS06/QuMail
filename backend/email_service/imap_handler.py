"""
IMAP Handler

Handles email retrieval and management via IMAP.
Uses imapclient for robust IMAP operations.
"""

import email
import logging
from datetime import datetime
from email.header import decode_header
from typing import Any, Dict, List, Optional, Tuple

from imapclient import IMAPClient

from config import settings
from .oauth2 import get_valid_token
from .mime_parser import parse_qumail_message

logger = logging.getLogger(__name__)

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993


def _decode_header_value(value: Any) -> str:
    """Decode an email header value."""
    if value is None:
        return ""
    
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("latin-1", errors="replace")
    
    if isinstance(value, str):
        return value
    
    decoded_parts = decode_header(str(value))
    result = []
    for data, charset in decoded_parts:
        if isinstance(data, bytes):
            result.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(str(data))
    
    return "".join(result)


def _parse_email_addresses(value: str) -> List[str]:
    """Parse email addresses from a header value."""
    if not value:
        return []
    
    from email.utils import parseaddr, getaddresses
    
    addresses = getaddresses([value])
    return [addr for name, addr in addresses if addr]


async def fetch_emails(
    folder: str = "INBOX",
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetch emails from the specified folder.
    
    Args:
        folder: IMAP folder name (INBOX, SENT, DRAFTS)
        offset: Number of emails to skip
        limit: Maximum emails to return
    
    Returns:
        Tuple of (emails list, total count)
    """
    from storage.database import get_stored_accounts
    
    accounts = await get_stored_accounts()
    if not accounts:
        return [], 0
    
    account = accounts[0]
    email_address = account["email"]
    access_token = await get_valid_token(email_address)
    
    imap_folder = _map_folder_name(folder)
    
    client = IMAPClient(GMAIL_IMAP_HOST, port=GMAIL_IMAP_PORT, ssl=True)
    
    try:
        client.oauth2_login(email_address, access_token)
        
        client.select_folder(imap_folder, readonly=True)
        
        all_messages = client.search(["ALL"])
        total = len(all_messages)
        
        all_messages.reverse()
        selected_ids = all_messages[offset:offset + limit]
        
        if not selected_ids:
            return [], total
        
        messages = client.fetch(
            selected_ids,
            ["RFC822.HEADER", "RFC822.SIZE", "FLAGS", "INTERNALDATE"]
        )
        
        emails = []
        for msg_id, data in messages.items():
            try:
                header_bytes = data.get(b"RFC822.HEADER", b"")
                msg = email.message_from_bytes(header_bytes)
                
                subject = _decode_header_value(msg.get("Subject", "(No Subject)"))
                from_addr = _decode_header_value(msg.get("From", ""))
                to_addrs = _parse_email_addresses(msg.get("To", ""))
                date = data.get(b"INTERNALDATE", datetime.now())
                flags = data.get(b"FLAGS", ())
                
                is_qumail = msg.get("X-QuMail-Version") is not None
                security_level = 4
                key_id = None
                
                if is_qumail:
                    security_level = int(msg.get("X-QuMail-Security-Level", "4"))
                    key_id = msg.get("X-QuMail-Key-ID")
                
                emails.append({
                    "message_id": str(msg_id),
                    "from": from_addr,
                    "to": to_addrs,
                    "subject": subject,
                    "preview": "",
                    "received_at": date if isinstance(date, datetime) else datetime.now(),
                    "security_level": security_level,
                    "key_id": key_id,
                    "encrypted": is_qumail and security_level < 4,
                    "is_read": b"\\Seen" in flags,
                    "attachments": [],
                })
                
            except Exception as e:
                logger.warning("Failed to parse email %s: %s", msg_id, e)
                continue
        
        return emails, total
        
    finally:
        try:
            client.logout()
        except:
            pass


async def get_email_by_id(message_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a complete email by its message ID.
    
    Args:
        message_id: IMAP message UID
    
    Returns:
        Complete email dict or None if not found
    """
    from storage.database import get_stored_accounts
    
    accounts = await get_stored_accounts()
    if not accounts:
        return None
    
    account = accounts[0]
    email_address = account["email"]
    access_token = await get_valid_token(email_address)
    
    client = IMAPClient(GMAIL_IMAP_HOST, port=GMAIL_IMAP_PORT, ssl=True)
    
    try:
        client.oauth2_login(email_address, access_token)
        client.select_folder("INBOX", readonly=True)
        
        messages = client.fetch([int(message_id)], ["RFC822"])
        
        if int(message_id) not in messages:
            return None
        
        raw_email = messages[int(message_id)][b"RFC822"]
        msg = email.message_from_bytes(raw_email)
        
        is_qumail = msg.get("X-QuMail-Version") is not None
        security_level = int(msg.get("X-QuMail-Security-Level", "4")) if is_qumail else 4
        key_id = msg.get("X-QuMail-Key-ID") if is_qumail else None
        
        if is_qumail and security_level < 4:
            parsed = parse_qumail_message(msg)
        else:
            parsed = _parse_regular_email(msg)
        
        return {
            "message_id": message_id,
            "from": _decode_header_value(msg.get("From", "")),
            "to": _parse_email_addresses(msg.get("To", "")),
            "cc": _parse_email_addresses(msg.get("Cc", "")),
            "subject": _decode_header_value(msg.get("Subject", "(No Subject)")),
            "body": parsed.get("body", ""),
            "encrypted_body": parsed.get("encrypted_body"),
            "html_body": parsed.get("html_body"),
            "attachments": parsed.get("attachments", []),
            "received_at": datetime.now(),
            "security_level": security_level,
            "key_id": key_id,
            "encrypted": is_qumail and security_level < 4,
            "encryption_metadata": parsed.get("metadata", {}),
        }
        
    except Exception as e:
        logger.exception("Failed to fetch email %s: %s", message_id, e)
        return None
    finally:
        try:
            client.logout()
        except:
            pass


async def delete_email(message_id: str) -> bool:
    """
    Delete an email by moving to trash.
    """
    from storage.database import get_stored_accounts
    
    accounts = await get_stored_accounts()
    if not accounts:
        return False
    
    account = accounts[0]
    email_address = account["email"]
    access_token = await get_valid_token(email_address)
    
    client = IMAPClient(GMAIL_IMAP_HOST, port=GMAIL_IMAP_PORT, ssl=True)
    
    try:
        client.oauth2_login(email_address, access_token)
        client.select_folder("INBOX")
        
        client.move([int(message_id)], "[Gmail]/Trash")
        
        return True
        
    except Exception as e:
        logger.exception("Failed to delete email %s: %s", message_id, e)
        return False
    finally:
        try:
            client.logout()
        except:
            pass


async def get_attachment_content(
    message_id: str,
    attachment_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Fetch attachment content from an email.
    """
    email_data = await get_email_by_id(message_id)
    if not email_data:
        return None
    
    for att in email_data.get("attachments", []):
        if att.get("id") == attachment_id:
            return att
    
    return None


def _map_folder_name(folder: str) -> str:
    """Map friendly folder names to IMAP folder paths."""
    mapping = {
        "INBOX": "INBOX",
        "SENT": "[Gmail]/Sent Mail",
        "DRAFTS": "[Gmail]/Drafts",
        "TRASH": "[Gmail]/Trash",
        "SPAM": "[Gmail]/Spam",
        "ALL": "[Gmail]/All Mail",
    }
    return mapping.get(folder.upper(), folder)


def _parse_regular_email(msg: email.message.Message) -> Dict[str, Any]:
    """Parse a regular (non-QuMail) email message."""
    body = ""
    html_body = None
    attachments = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" in disposition:
                attachments.append({
                    "id": str(hash(part.get_filename() or "")),
                    "filename": part.get_filename() or "unnamed",
                    "content_type": content_type,
                    "size": len(part.get_payload(decode=True) or b""),
                    "content": part.get_payload(decode=True),
                })
            elif content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html_body = payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")
    
    return {
        "body": body,
        "html_body": html_body,
        "attachments": attachments,
    }
