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
