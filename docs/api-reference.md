# QuMail API Reference

## Backend API (localhost:8000)

All endpoints require Bearer token authentication except `/health`.

### Authentication

#### POST /api/v1/auth/token
Generate session token for frontend-backend communication.

**Request:**
```json
{
  "app_secret": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### POST /api/v1/auth/oauth/gmail/init
Initialize Gmail OAuth2 flow.

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/...",
  "state": "random_state_token"
}
```

#### GET /api/v1/auth/oauth/gmail/callback
Complete OAuth2 authentication.

**Query Parameters:**
- `code`: Authorization code from Google
- `state`: State token from init

**Response:**
```json
{
  "success": true,
  "email": "user@gmail.com"
}
```

### Emails

#### GET /api/v1/emails
Fetch emails from a folder.

**Query Parameters:**
- `folder`: INBOX, SENT, DRAFTS (default: INBOX)
- `page`: Page number (default: 1)
- `limit`: Emails per page, max 50 (default: 20)
- `decrypt`: Auto-decrypt emails (default: true)

**Response:**
```json
{
  "emails": [
    {
      "message_id": "123",
      "from": "sender@example.com",
      "to": ["recipient@example.com"],
      "subject": "Test Email",
      "preview": "Email preview text...",
      "received_at": "2026-01-12T10:30:00Z",
      "security_level": 2,
      "has_attachments": false,
      "is_read": true
    }
  ],
  "total": 100,
  "has_more": true
}
```

#### GET /api/v1/emails/{message_id}
Get full email content with decryption.

**Response:**
```json
{
  "message_id": "123",
  "from": "sender@example.com",
  "to": ["recipient@example.com"],
  "cc": [],
  "subject": "Test Email",
  "body": "Decrypted email content",
  "html_body": null,
  "attachments": [],
  "received_at": "2026-01-12T10:30:00Z",
  "security_level": 2,
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "decryption_status": "success"
}
```

#### POST /api/v1/emails/send
Send an encrypted email.

**Request:**
```json
{
  "to": ["recipient@example.com"],
  "cc": [],
  "subject": "Test Email",
  "body": "Email content",
  "security_level": 2
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "<uuid@qumail.local>",
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "security_level_used": 2
}
```

#### DELETE /api/v1/emails/{message_id}
Delete an email.

**Response:**
```json
{
  "success": true,
  "message_id": "123"
}
```

### Security

#### GET /api/v1/security/status
Get security and Key Manager status.

**Response:**
```json
{
  "km_connected": true,
  "km_url": "http://127.0.0.1:8100",
  "available_key_material": {
    "otp_bytes": 10485760,
    "aes_keys": 1000,
    "pqc_keys": 0
  },
  "last_key_sync": "2026-01-12T10:30:00Z",
  "supported_levels": [1, 2, 3, 4]
}
```

#### GET /api/v1/security/capabilities/{email}
Check recipient's QuMail capabilities.

**Response:**
```json
{
  "email": "recipient@example.com",
  "is_qumail_user": true,
  "supported_levels": [2, 3, 4],
  "public_key_fingerprint": "SHA256:abc123..."
}
```

#### POST /api/v1/security/refresh-keys
Request more key material.

**Request:**
```json
{
  "key_type": "aes",
  "size": 1000
}
```

**Response:**
```json
{
  "success": true,
  "keys_added": 1000
}
```

---

## Key Manager API (localhost:8100)

ETSI GS QKD 014-style REST API.

### POST /api/v1/keys/request
Request new key material.

**Request:**
```json
{
  "peer_id": "recipient@example.com",
  "size": 32,
  "key_type": "aes_seed"
}
```

**Response:**
```json
{
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "key_material": "base64_encoded_key",
  "peer_id": "recipient@example.com",
  "key_type": "aes_seed",
  "created_at": "2026-01-12T10:30:00Z",
  "expires_at": "2026-01-13T10:30:00Z"
}
```

### GET /api/v1/keys/{key_id}
Retrieve key by ID.

**Response:**
```json
{
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "key_material": "base64_encoded_key",
  "peer_id": "recipient@example.com",
  "key_type": "aes_seed",
  "used": false,
  "created_at": "2026-01-12T10:30:00Z"
}
```

**Error (410 Gone):** Key already consumed

### POST /api/v1/keys/{key_id}/consume
Mark key as consumed (required for OTP).

**Response:**
```json
{
  "success": true,
  "consumed_at": "2026-01-12T10:31:00Z"
}
```

### GET /api/v1/keys/status
Get available key material.

**Response:**
```json
{
  "otp_bytes_available": 10485760,
  "aes_keys_available": 1000,
  "pqc_keys_available": 0
}
```
