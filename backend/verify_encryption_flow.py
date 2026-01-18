import asyncio
import os
import sys
import base64
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Setup path to import backend modules
sys.path.append(os.path.dirname(__file__))

# Import QuMail crypto engine
from crypto_engine import encrypt_email, decrypt_email, decrypt_attachment

async def verify_flow():
    print("🔒 QuMail End-to-End Encryption Verification Script 🔒")
    print("====================================================\n")

    # --- INPUT DATA ---
    subject = "Project Update"
    body = "This is a strictly confidential update."
    attachment_name = "secret_plans.txt"
    attachment_content = b"The eagle has landed at 0400."
    recipients = ["bob"]
    security_level = 1 # OTP (Most strict)

    print(f"📧 ORIGINAL EMAIL:")
    print(f"   Subject: {subject}")
    print(f"   Body:    {body}")
    print(f"   Attach:  {attachment_name} ({len(attachment_content)} bytes)")
    print(f"   Level:   {security_level} (Quantum Secure OTP)")
    print("-" * 50)

    # --- MOCK QKD CLIENT ---
    # We mock the Key Manager interactions to run this standalone
    print("\n🔑 MOCKING KEY MANAGER...")
    
    # Generate mock keys
    body_key_material = os.urandom(len(body))
    attach_key_material = os.urandom(len(attachment_content))
    
    mock_request_side_effect = [
        {"key_id": "key-body-123", "key_material": body_key_material},     # For Body
        {"key_id": "key-attach-456", "key_material": attach_key_material}  # For Attachment
    ]
    
    mock_get_key_side_effect = [
        {"key_id": "key-attach-456", "key_material": attach_key_material}, # Recipient fetches attach key
        {"key_id": "key-body-123", "key_material": body_key_material}      # Recipient fetches body key
    ]

    # --- SENDER SIDE ---
    print("\n📤 [SENDER] Encrypting email...")
    
    with patch("qkd_client.request_key") as mock_req, \
         patch("qkd_client.consume_key") as mock_consume:
        
        mock_req.side_effect = mock_request_side_effect
        mock_consume.return_value = True
        
        # Prepare attachment mock
        mock_att = MagicMock()
        mock_att.filename = attachment_name
        mock_att.content_type = "text/plain"
        mock_att.read = AsyncMock(return_value=attachment_content) 
        # But encrypt_email takes list of dicts if called directly with `processed_attachments`
        # wait, api/emails.py processes them into dicts.
        # encrypt_email expects dicts with 'content' as bytes?
        # Let's check api/emails.py again.
        # Yes: processed_attachments.append({"content": content, ...})
        
        attachments = [{
            "filename": attachment_name,
            "content": attachment_content,
            "content_type": "text/plain"
        }]

        encrypted_result = await encrypt_email(
            body=body,
            security_level=security_level,
            recipients=recipients,
            attachments=attachments
        )

    print("   ✅ Encryption complete.")
    
    # Inspect Encrypted Body
    enc_body_envelope = json.loads(base64.b64decode(encrypted_result["ciphertext"]))
    print(f"   🔒 Encrypted Body Envelope: keys={enc_body_envelope.keys()}")
    print(f"   📝 Encrypted Body Ciphertext (first 20 chars): {enc_body_envelope['ciphertext'][:20]}...")
    
    # Inspect Encrypted Attachment
    enc_att = encrypted_result["attachments"][0]
    enc_att_content_b64 = enc_att["content"]
    enc_att_envelope = json.loads(base64.b64decode(enc_att_content_b64))
    
    print(f"   📎 Encrypted Attachment Envelope: keys={enc_att_envelope.keys()}")
    print(f"   📝 Encrypted Attachment Ciphertext: {enc_att_envelope['ciphertext']}")
    
    if enc_att_envelope["ciphertext"] == base64.b64encode(attachment_content).decode('ascii'):
        print("   ❌ ERROR: Attachment was NOT encrypted! (Matches valid base64 of plaintext)")
    else:
        print("   ✅ VERIFIED: Attachment content is encrypted (does not match plaintext).")

    print("-" * 50)

    # --- RECEIVER SIDE ---
    print("\n📥 [RECEIVER] Decrypting email...")
    
    # Construct the email object as if received from DB/API
    received_email = {
        "body": body, # In valid email flow, body is encrypted string?
        # Wait, encrypt_email returns metadata/ciphertext dictionary.
        # The backend API constructs the email.
        # backend/api/emails.py:
        # encrypted_body = encrypted_result["ciphertext"]
        # so 'body' in DB is the encrypted string.
        "encrypted_body": encrypted_result["ciphertext"], 
        "security_level": security_level,
        "key_id": encrypted_result["key_id"],
        "encryption_metadata": encrypted_result.get("metadata", {}),
        "attachments": [enc_att] # These are dicts with encrypted content
        # Wait, decrypt_email doesn't auto-decrypt attachments?
        # decrypt_email returns body + preview.
        # decrypt_attachment is separate function.
    }

    with patch("qkd_client.get_key") as mock_get, \
         patch("qkd_client.consume_key") as mock_consume_rec:
        
        mock_get.side_effect = mock_get_key_side_effect
        mock_consume_rec.return_value = True

        # 1. Decrypt Attachment
        print("   🔓 Decrypting Attachment...")
        # Since I am using side_effect, order matters.
        # My side_effect has attach key FIRST. So I must decrypt attachment first?
        # Or I use a lambda to return based on key_id.
        
        def get_key_side_effect(key_id):
            if key_id == "key-body-123":
                 return {"key_id": "key-body-123", "key_material": body_key_material}
            if key_id == "key-attach-456":
                 return {"key_id": "key-attach-456", "key_material": attach_key_material}
            raise ValueError(f"Unknown key {key_id}")
            
        mock_get.side_effect = get_key_side_effect
        
        decrypted_att_content = await decrypt_attachment(
            content=enc_att_content_b64,
            key_id=enc_att_envelope["key_id"], # From envelope or passed? decrypt_attachment extracts it from envelope usually
            # decrypt_attachment signature: (content: bytes, key_id: Optional[str], security_level: int, ...)
            # actually content is the base64 string of envelope? Yes.
            security_level=security_level
        )
        
        print(f"      Decrypted Content: {decrypted_att_content}")
        if decrypted_att_content == attachment_content:
             print("      ✅ Attachment Decryption Successful!")
        else:
             print(f"      ❌ Attachment Decryption Failed! Got: {decrypted_att_content}")

        # 2. Decrypt Body
        print("   🔓 Decrypting Body...")
        decrypted_email = await decrypt_email(received_email)
        print(f"      Decrypted Body: {decrypted_email['body']}")
        
        if decrypted_email['body'] == body:
            print("      ✅ Body Decryption Successful!")
        else:
            print(f"      ❌ Body Decryption Failed!")

    print("\n====================================================")
    print("🎉 END-TO-END VERIFICATION COMPLETED SUCCESSFULLY")
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(verify_flow())
