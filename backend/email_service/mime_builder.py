"""
MIME Message Builder

Constructs encrypted email MIME messages following the QuMail wire format.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Optional


QUMAIL_BOUNDARY = "=_QuMail_Boundary_v1"


def build_encrypted_mime(
    from_addr: str,
    to_addrs: List[str],
    cc_addrs: List[str],
    subject: str,
    encrypted_body: str,
    security_level: int,
    key_id: Optional[str] = None,
    attachments: Optional[List[dict]] = None,
) -> MIMEMultipart:
    """
    Build a MIME message with encrypted content.
    
    The message follows the QuMail wire format:
    - Standard email headers (readable by servers)
    - X-QuMail-* headers for encryption metadata
    - Encrypted body as application/x-qumail-envelope
    - Encrypted attachments as application/x-qumail-attachment
    
    Args:
        from_addr: Sender email address
        to_addrs: List of recipient addresses
        cc_addrs: List of CC addresses
        subject: Email subject (visible to servers)
        encrypted_body: Base64-encoded encrypted content
        security_level: 1 (OTP), 2 (AES), 3 (PQC)
        key_id: Key identifier for decryption
        attachments: Optional encrypted attachments
    
    Returns:
        MIMEMultipart message ready for sending
    """
    message = MIMEMultipart("mixed", boundary=QUMAIL_BOUNDARY)
    
    message["From"] = from_addr
    message["To"] = ", ".join(to_addrs)
    if cc_addrs:
        message["Cc"] = ", ".join(cc_addrs)
    message["Subject"] = f"[QuMail Encrypted] {subject}"
    
    message["X-QuMail-Version"] = "1.0"
    message["X-QuMail-Security-Level"] = str(security_level)
    
    if key_id:
        message["X-QuMail-Key-ID"] = key_id
    
    algorithm_map = {
        1: "OTP-XOR",
        2: "AES-256-GCM",
        3: "KYBER-768-AES-256-GCM",
    }
    message["X-QuMail-Algorithm"] = algorithm_map.get(security_level, "UNKNOWN")
    
    envelope = MIMEApplication(
        encrypted_body.encode("utf-8"),
        _subtype="x-qumail-envelope",
        _encoder=lambda x: x,
    )
    envelope.set_charset("utf-8")
    envelope["Content-Transfer-Encoding"] = "base64"
    message.attach(envelope)
    
    if attachments:
        for att in attachments:
            att_part = MIMEApplication(
                att["content"],
                _subtype="x-qumail-attachment",
            )
            att_part["Content-Disposition"] = f'attachment; filename="{att["filename"]}.enc"'
            att_part["X-QuMail-Original-Name"] = att["filename"]
            att_part["X-QuMail-Original-Size"] = str(att.get("original_size", len(att["content"])))
            att_part["Content-Transfer-Encoding"] = "base64"
            message.attach(att_part)
    
    return message


def build_plain_mime(
    from_addr: str,
    to_addrs: List[str],
    cc_addrs: List[str],
    subject: str,
    body: str,
    attachments: Optional[List[dict]] = None,
) -> MIMEMultipart:
    """
    Build a standard unencrypted MIME message.
    
    Used for Level 4 (no security) emails.
    """
    if attachments:
        message = MIMEMultipart("mixed")
    else:
        message = MIMEMultipart("alternative")
    
    message["From"] = from_addr
    message["To"] = ", ".join(to_addrs)
    if cc_addrs:
        message["Cc"] = ", ".join(cc_addrs)
    message["Subject"] = subject
    
    text_part = MIMEText(body, "plain", "utf-8")
    message.attach(text_part)
    
    if attachments:
        for att in attachments:
            att_part = MIMEApplication(att["content"], Name=att["filename"])
            att_part["Content-Disposition"] = f'attachment; filename="{att["filename"]}"'
            message.attach(att_part)
    
    return message
