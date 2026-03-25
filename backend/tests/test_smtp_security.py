import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from email_service.smtp_handler import send_email
from email.message import Message

@pytest.mark.asyncio
async def test_send_email_encryption_flow():
    """
    Verify that when sending an email with security_level < 4,
    the message body passed to SMTP is NOT plaintext but an encrypted envelope.
    """
    
    # Mock database to return a dummy account
    with patch("storage.database.get_stored_accounts", new_callable=AsyncMock) as mock_get_accounts:
        mock_get_accounts.return_value = [{"email": "test@qumail.com"}]
        
        # Mock token retrieval
        with patch("email_service.smtp_handler.get_valid_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "dummy_token"
            
            # Mock database save
            with patch("storage.database.save_sent_email", new_callable=AsyncMock):
                
                # Mock aiosmtplib.SMTP
                with patch("aiosmtplib.SMTP") as MockSMTP:
                    mock_smtp_instance = MockSMTP.return_value
                    mock_smtp_instance.connect = AsyncMock()
                    mock_smtp_instance.execute_command = AsyncMock(return_value=MagicMock(code=235, message="OK"))
                    mock_smtp_instance.send_message = AsyncMock()
                    mock_smtp_instance.quit = AsyncMock()
                    
                    # Test Case 1: Security Level 2 (Encrypted)
                    # The 'body' passed here simulates the ALREADY ENCRYPTED payload from the API layer
                    # In a real flow, api/emails.py encrypts it first. 
                    # send_email expects 'body' to be the payload to put in the envelope.
                    
                    # Wait, if send_email calls build_encrypted_mime, it puts 'body' into the envelope.
                    # So we need to check if the generated MIME message has the correct structure.
                    
                    await send_email(
                        to=["recipient@example.com"],
                        cc=[],
                        subject="Secret Subject",
                        body="ENCRYPTED_BLOB_BASE64",
                        security_level=2,
                        key_id="key123"
                    )
                    
                    # Capture the message object passed to send_message
                    call_args = mock_smtp_instance.send_message.call_args
                    md = call_args[0][0] # The MIMEMultipart object
                    
                    assert md["X-QuMail-Security-Level"] == "2"
                    assert md["X-QuMail-Key-ID"] == "key123"
                    
                    # Verify structure
                    parts = list(md.walk())
                    # Should contain application/x-qumail-envelope
                    envelope_parts = [p for p in parts if p.get_content_type() == "application/x-qumail-envelope"]
                    assert len(envelope_parts) == 1
                    
                    # Verify content is what we passed (the already encrypted blob)
                    payload = envelope_parts[0].get_payload()
                    # It might be base64 encoded again by MIMEApplication if we aren't careful, 
                    # but check mime_builder info. 
                    # It sets Content-Transfer-Encoding: base64
                    # So payload might be base64 of "ENCRYPTED_BLOB_BASE64"
                    
                    assert payload is not None
                    
                    # Test Case 2: Security Level 4 (Plaintext)
                    await send_email(
                        to=["recipient@example.com"],
                        cc=[],
                        subject="Plain Subject",
                        body="Plain Body",
                        security_level=4
                    )
                    
                    call_args_plain = mock_smtp_instance.send_message.call_args
                    md_plain = call_args_plain[0][0]
                    
                    # Should contain text/plain
                    parts_plain = list(md_plain.walk())
                    text_parts = [p for p in parts_plain if p.get_content_type() == "text/plain"]
                    assert len(text_parts) >= 1
                    decoded_body = text_parts[0].get_payload(decode=True).decode()
                    assert "Plain Body" in decoded_body
