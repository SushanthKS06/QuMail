import base64
import email
import imaplib
import logging
from datetime import datetime
from email.header import decode_header
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from .oauth2 import get_valid_token
from .mime_parser import parse_qumail_message

logger = logging.getLogger(__name__)

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993

YAHOO_IMAP_HOST = "imap.mail.yahoo.com"
YAHOO_IMAP_PORT = 993


def _decode_header_value(value: Any) -> str:
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
    if not value:
        return []
    
    from email.utils import parseaddr, getaddresses
    
    addresses = getaddresses([value])
    return [addr for name, addr in addresses if addr]


def _get_imap_config(email_address: str) -> Tuple[str, int]:
    """Get IMAP host and port based on email provider."""
    email_lower = email_address.lower()
    if "@yahoo" in email_lower or "@ymail" in email_lower:
        return YAHOO_IMAP_HOST, YAHOO_IMAP_PORT
    return GMAIL_IMAP_HOST, GMAIL_IMAP_PORT


def _oauth2_authenticate(imap: imaplib.IMAP4_SSL, email_address: str, access_token: str) -> None:
    """Authenticate using XOAUTH2."""
    # XOAUTH2 auth string format: user=<email>\x01auth=Bearer <token>\x01\x01
    auth_string = f"user={email_address}\x01auth=Bearer {access_token}\x01\x01"
    
    def auth_callback(response):
        # imaplib expects raw bytes, it will handle base64 encoding
        return auth_string.encode("utf-8")
    
    try:
        imap.authenticate("XOAUTH2", auth_callback)
    except imaplib.IMAP4.error as e:
        logger.error("XOAUTH2 authentication failed: %s", e)
        raise


async def fetch_emails(
    folder: str = "INBOX",
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:
    from storage.database import get_stored_accounts
    
    accounts = await get_stored_accounts()
    if not accounts:
        return [], 0
    
    account = accounts[0]
    email_address = account["email"]
    access_token = await get_valid_token(email_address)
    
    imap_folder = _map_folder_name(folder, email_address)
    imap_host, imap_port = _get_imap_config(email_address)
    
    imap = imaplib.IMAP4_SSL(imap_host, imap_port)
    
    try:
        _oauth2_authenticate(imap, email_address, access_token)
        
        # Quote folder name for IMAP - folders with special chars need quotes
        quoted_folder = f'"{imap_folder}"' if " " in imap_folder or "[" in imap_folder else imap_folder
        status, data = imap.select(quoted_folder, readonly=True)
        if status != "OK":
            logger.error("Failed to select folder %s: %s", imap_folder, data)
            return [], 0
        
        status, data = imap.search(None, "ALL")
        if status != "OK":
            return [], 0
        
        all_messages = data[0].split()
        total = len(all_messages)
        
        all_messages.reverse()
        selected_ids = all_messages[offset:offset + limit]
        
        if not selected_ids:
            return [], total
        
        emails = []
        for msg_id in selected_ids:
            try:
                status, data = imap.fetch(msg_id, "(RFC822.HEADER FLAGS INTERNALDATE)")
                if status != "OK" or not data or data[0] is None:
                    continue
                
                raw_data = data[0]
                if isinstance(raw_data, tuple) and len(raw_data) >= 2:
                    header_bytes = raw_data[1]
                else:
                    continue
                
                msg = email.message_from_bytes(header_bytes)
                
                subject = _decode_header_value(msg.get("Subject", "(No Subject)"))
                from_addr = _decode_header_value(msg.get("From", ""))
                to_addrs = _parse_email_addresses(msg.get("To", ""))
                
                is_qumail = msg.get("X-QuMail-Version") is not None
                security_level = 4
                key_id = None
                
                if is_qumail:
                    security_level = int(msg.get("X-QuMail-Security-Level", "4"))
                    key_id = msg.get("X-QuMail-Key-ID")
                
                flags_str = str(data[0]) if data[0] else ""
                is_read = "\\Seen" in flags_str
                
                emails.append({
                    "message_id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                    "from": from_addr,
                    "to": to_addrs,
                    "subject": subject,
                    "preview": "",
                    "received_at": datetime.now(),
                    "security_level": security_level,
                    "key_id": key_id,
                    "encrypted": is_qumail and security_level < 4,
                    "is_read": is_read,
                    "attachments": [],
                })
                
            except Exception as e:
                logger.warning("Failed to parse email %s: %s", msg_id, e)
                continue
        
        return emails, total
        
    finally:
        try:
            imap.logout()
        except:
            pass


async def get_email_by_id(message_id: str) -> Optional[Dict[str, Any]]:
    from storage.database import get_stored_accounts
    
    accounts = await get_stored_accounts()
    if not accounts:
        return None
    
    account = accounts[0]
    email_address = account["email"]
    access_token = await get_valid_token(email_address)
    
    imap_host, imap_port = _get_imap_config(email_address)
    imap = imaplib.IMAP4_SSL(imap_host, imap_port)
    
    try:
        _oauth2_authenticate(imap, email_address, access_token)
        imap.select("INBOX", readonly=True)
        
        status, data = imap.fetch(message_id.encode() if isinstance(message_id, str) else message_id, "(RFC822)")
        
        if status != "OK" or not data or data[0] is None:
            return None
        
        raw_data = data[0]
        if isinstance(raw_data, tuple) and len(raw_data) >= 2:
            raw_email = raw_data[1]
        else:
            return None
        
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
            imap.logout()
        except:
            pass


async def delete_email(message_id: str) -> bool:
    from storage.database import get_stored_accounts
    
    accounts = await get_stored_accounts()
    if not accounts:
        return False
    
    account = accounts[0]
    email_address = account["email"]
    access_token = await get_valid_token(email_address)
    
    imap_host, imap_port = _get_imap_config(email_address)
    imap = imaplib.IMAP4_SSL(imap_host, imap_port)
    
    try:
        _oauth2_authenticate(imap, email_address, access_token)
        imap.select("INBOX")
        
        trash_folder = _get_trash_folder(email_address)
        msg_id = message_id.encode() if isinstance(message_id, str) else message_id
        
        # Quote folder name for copy command
        quoted_trash = f'"{trash_folder}"' if " " in trash_folder or "[" in trash_folder else trash_folder
        imap.copy(msg_id, quoted_trash)
        imap.store(msg_id, "+FLAGS", "\\Deleted")
        imap.expunge()
        
        return True
        
    except Exception as e:
        logger.exception("Failed to delete email %s: %s", message_id, e)
        return False
    finally:
        try:
            imap.logout()
        except:
            pass


async def get_attachment_content(
    message_id: str,
    attachment_id: str,
) -> Optional[Dict[str, Any]]:
    email_data = await get_email_by_id(message_id)
    if not email_data:
        return None
    
    for att in email_data.get("attachments", []):
        if att.get("id") == attachment_id:
            return att
    
    return None


def _map_folder_name(folder: str, email_address: str = "") -> str:
    """Map folder name to provider-specific folder."""
    email_lower = email_address.lower() if email_address else ""
    is_yahoo = "@yahoo" in email_lower or "@ymail" in email_lower
    
    if is_yahoo:
        mapping = {
            "INBOX": "INBOX",
            "SENT": "Sent",
            "DRAFTS": "Draft",
            "TRASH": "Trash",
            "SPAM": "Bulk Mail",
            "ALL": "INBOX",
        }
    else:
        mapping = {
            "INBOX": "INBOX",
            "SENT": "[Gmail]/Sent Mail",
            "DRAFTS": "[Gmail]/Drafts",
            "TRASH": "[Gmail]/Trash",
            "SPAM": "[Gmail]/Spam",
            "ALL": "[Gmail]/All Mail",
        }
    return mapping.get(folder.upper(), folder)


def _get_trash_folder(email_address: str) -> str:
    """Get the trash folder name for the email provider."""
    email_lower = email_address.lower()
    if "@yahoo" in email_lower or "@ymail" in email_lower:
        return "Trash"
    return "[Gmail]/Trash"


def _parse_regular_email(msg: email.message.Message) -> Dict[str, Any]:
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
