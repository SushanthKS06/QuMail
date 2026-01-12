# QuMail - Quantum Secure Email Client Implementation Plan

## Overview

QuMail is a production-grade, Windows desktop email client that provides quantum-secure communication over existing email infrastructure. It works with standard email providers (Gmail, Yahoo, etc.) by performing application-layer encryption before transmission—email servers see only encrypted blobs, remaining completely unchanged.

### Key Design Principles

1. **Defense in Depth**: Multiple layers of security; compromise of one layer doesn't break the system
2. **Zero Trust**: Assume network and email servers are hostile
3. **Separation of Concerns**: Crypto never touches the frontend; UI never handles keys
4. **Forward Secrecy**: One-time keys (OTP mode) provide information-theoretic security
5. **Modularity**: Each component is replaceable without affecting others

---

## Phase 1 – System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           QuMail Desktop Application                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Electron Shell (Windows Desktop)                      ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │                     React Frontend (TypeScript)                      │││
│  │  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐  │││
│  │  │  │  Compose UI  │ │  Inbox UI    │ │  Security Level Selector    │  │││
│  │  │  │              │ │              │ │  [OTP][AES][PQC][PLAIN]     │  │││
│  │  │  └──────────────┘ └──────────────┘ └─────────────────────────────┘  │││
│  │  │  ┌────────────────────────────────────────────────────────────────┐ │││
│  │  │  │                    REST API Client Layer                        │ │││
│  │  │  │   (auth tokens, request signing, response validation)          │ │││
│  │  │  └────────────────────────────────────────────────────────────────┘ │││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP (127.0.0.1:8000)
                                      │ Token-Protected APIs
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Python FastAPI Backend (Security Core)                  │
│                         Binds to 127.0.0.1 ONLY                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                            API Gateway Layer                             ││
│  │         (Authentication, Rate Limiting, Request Validation)              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │
│  │ Email Service│ │Crypto Engine │ │  QKD Client  │ │   Policy Engine    │  │
│  │              │ │              │ │              │ │                    │  │
│  │ • SMTP       │ │ • AES-GCM    │ │ • KM REST    │ │ • Security Rules   │  │
│  │ • IMAP       │ │ • OTP Logic  │ │ • Key Fetch  │ │ • Mode Validation  │  │
│  │ • OAuth2     │ │ • PQC Ops    │ │ • Key Track  │ │ • Recipient Check  │  │
│  │ • Parse/Build│ │ • Key Derive │ │ • ETSI 014   │ │ • Attachment Policy│  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘  │
│  ┌──────────────────────────────────┐ ┌────────────────────────────────────┐│
│  │           Key Store              │ │           Storage                   ││
│  │                                  │ │                                    ││
│  │ • In-memory session keys         │ │ • SQLite (encrypted)               ││
│  │ • Encrypted disk cache           │ │ • Email metadata cache             ││
│  │ • Key usage tracking             │ │ • Attachment storage               ││
│  │ • Automatic key zeroization      │ │ • Audit logs                       ││
│  └──────────────────────────────────┘ └────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP (127.0.0.1:8100)
                                      │ mTLS / Token Auth
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Simulated QKD Key Manager (ETSI GS QKD 014)                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       Key Provisioning Engine                         │   │
│  │                                                                       │   │
│  │   Peer A (sender@domain.com) ◄────────────────► Peer B (recipient)    │   │
│  │              │                                        │               │   │
│  │              ▼                                        ▼               │   │
│  │   ┌─────────────────┐                    ┌─────────────────┐          │   │
│  │   │   Key Pool A    │    Synchronized    │   Key Pool B    │          │   │
│  │   │   key_id: uuid  │◄──────────────────►│   key_id: uuid  │          │   │
│  │   │   material: []  │                    │   material: []  │          │   │
│  │   │   used: false   │                    │   used: false   │          │   │
│  │   └─────────────────┘                    └─────────────────┘          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  REST API Endpoints:                                                         │
│    POST /api/v1/keys/request     - Request new key material                  │
│    GET  /api/v1/keys/{key_id}    - Retrieve key by ID                        │
│    POST /api/v1/keys/{key_id}/consume - Mark key as used (OTP)               │
│    GET  /api/v1/keys/status      - Check available key material              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (Simulated QKD Channel)
                                      │ In production: Fiber optic + QKD hardware
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        External Email Infrastructure                         │
│                          (Gmail, Yahoo, etc.)                                │
│                                                                              │
│   ┌────────────────┐        ┌────────────────┐        ┌────────────────┐    │
│   │   SMTP Server  │        │   IMAP Server  │        │   OAuth2       │    │
│   │   (Outbound)   │        │   (Inbound)    │        │   Provider     │    │
│   │                │        │                │        │                │    │
│   │ Sees only:     │        │ Stores only:   │        │ Provides:      │    │
│   │ • Headers      │        │ • Encrypted    │        │ • Access tokens│    │
│   │ • Encrypted    │        │   blobs        │        │ • Refresh flow │    │
│   │   body blob    │        │ • Metadata     │        │                │    │
│   └────────────────┘        └────────────────┘        └────────────────┘    │
│                                                                              │
│   🔒 Servers NEVER see plaintext email content                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### 1. Electron Shell
| Responsibility | Description |
|----------------|-------------|
| Window Management | Creates native Windows window, handles minimize/maximize/close |
| Process Isolation | Runs React in renderer process, Python backend as child process |
| IPC Bridge | Secure inter-process communication between frontend and backend |
| Auto-Updates | (Future) Handles application updates |
| System Tray | Background operation, notifications |

#### 2. React Frontend (TypeScript)
| Responsibility | Description |
|----------------|-------------|
| UI Rendering | All visual elements: inbox, compose, settings |
| User Input | Captures email content, recipient addresses, security level selection |
| API Communication | Sends requests to Python backend via REST |
| State Management | Local UI state only (no keys, no crypto) |
| Security Level UX | Clear visual indicators of encryption status |

> [!CAUTION]
> The frontend NEVER handles cryptographic keys, performs encryption, or accesses email protocols directly. All sensitive operations are delegated to the backend.

#### 3. Python FastAPI Backend

##### Email Service (`/email_service`)
| Function | Description |
|----------|-------------|
| SMTP Handler | Async email sending via `aiosmtplib` |
| IMAP Handler | Email retrieval via `imapclient`, folder management |
| OAuth2 Flow | Gmail OAuth2 authentication, token refresh |
| MIME Builder | Constructs encrypted email messages |
| MIME Parser | Parses incoming emails, extracts encrypted payloads |

##### Crypto Engine (`/crypto_engine`)
| Function | Description |
|----------|-------------|
| OTP Encryption | XOR-based encryption with exact key length matching |
| AES-GCM | 256-bit key, authenticated encryption |
| PQC Operations | Kyber key encapsulation, Dilithium signatures |
| Key Derivation | HKDF for deriving session keys from QKD material |
| Secure Comparison | Constant-time comparison to prevent timing attacks |

##### QKD Client (`/qkd_client`)
| Function | Description |
|----------|-------------|
| Key Request | Requests new key material from KM |
| Key Retrieval | Fetches key by ID for decryption |
| Key Consumption | Marks OTP keys as used (one-time enforcement) |
| Status Check | Monitors available key material |
| Retry Logic | Handles KM unavailability gracefully |

##### Key Store (`/key_store`)
| Function | Description |
|----------|-------------|
| Session Cache | In-memory storage for active session keys |
| Encrypted Disk | AES-encrypted local key cache for offline use |
| Usage Tracking | Prevents key reuse for OTP mode |
| Zeroization | Secure memory clearing after use |
| Expiry Management | Automatic removal of expired keys |

##### Policy Engine (`/policy_engine`)
| Function | Description |
|----------|-------------|
| Mode Validation | Ensures requested security level is available |
| Recipient Check | Verifies recipient can receive encrypted email |
| Key Sufficiency | Checks if enough key material exists for OTP |
| Fallback Rules | Handles degradation scenarios |
| Audit Generation | Logs security-relevant decisions |

##### Storage (`/storage`)
| Function | Description |
|----------|-------------|
| SQLite DB | Encrypted local database for email metadata |
| Attachment Cache | Encrypted storage for attachments |
| Draft Storage | Auto-save drafts with encryption |
| Audit Logs | Immutable security event logs |

#### 4. Simulated Key Manager (KM)
| Responsibility | Description |
|----------------|-------------|
| Key Generation | Generates cryptographically random key material (simulating QKD output) |
| Peer Provisioning | Pre-provisions symmetric keys for peer pairs |
| ETSI Compliance | Implements ETSI GS QKD 014 REST API structure |
| One-Time Enforcement | Marks OTP keys as consumed, prevents reuse |
| Key Exhaustion | Returns errors when key pool is depleted |
| Status Reporting | Reports available key material per peer |

---

### Data Flow Diagrams

#### Sending an Encrypted Email (Level 2 - AES-GCM)

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │     │  React  │     │ FastAPI │     │   KM    │     │ Crypto  │     │  SMTP   │
│         │     │Frontend │     │ Backend │     │         │     │ Engine  │     │ Server  │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │               │               │
     │ Compose email │               │               │               │               │
     │ Select AES    │               │               │               │               │
     │ Click Send    │               │               │               │               │
     │───────────────►│               │               │               │               │
     │               │               │               │               │               │
     │               │ POST /api/send│               │               │               │
     │               │ {to, subject, │               │               │               │
     │               │  body, level=2}               │               │               │
     │               │───────────────►│               │               │               │
     │               │               │               │               │               │
     │               │               │ 1. Validate request            │               │
     │               │               │ 2. Check recipient capability  │               │
     │               │               │               │               │               │
     │               │               │POST /keys/request              │               │
     │               │               │{peer_id, size=32}              │               │
     │               │               │───────────────►│               │               │
     │               │               │               │               │               │
     │               │               │    {key_id, key_material}      │               │
     │               │               │◄───────────────│               │               │
     │               │               │               │               │               │
     │               │               │ encrypt(body, key)             │               │
     │               │               │───────────────────────────────►│               │
     │               │               │               │               │               │
     │               │               │    {ciphertext, nonce, tag}    │               │
     │               │               │◄───────────────────────────────│               │
     │               │               │               │               │               │
     │               │               │ 3. Build MIME message          │               │
     │               │               │    - Keep headers readable     │               │
     │               │               │    - Include encrypted blob    │               │
     │               │               │    - Add X-QuMail-* headers    │               │
     │               │               │               │               │               │
     │               │               │ 4. Send via SMTP               │               │
     │               │               │─────────────────────────────────────────────────►│
     │               │               │               │               │               │
     │               │               │         250 OK                 │               │
     │               │◄───────────────│               │               │               │
     │               │               │               │               │               │
     │  ✓ Sent!      │               │               │               │               │
     │◄───────────────│               │               │               │               │
     │               │               │               │               │               │
```

#### Receiving and Decrypting an Email

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │     │  React  │     │ FastAPI │     │  IMAP   │     │   KM    │     │ Crypto  │
│         │     │Frontend │     │ Backend │     │ Server  │     │         │     │ Engine  │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │               │               │
     │ Open Inbox    │               │               │               │               │
     │───────────────►│               │               │               │               │
     │               │               │               │               │               │
     │               │GET /api/emails│               │               │               │
     │               │───────────────►│               │               │               │
     │               │               │               │               │               │
     │               │               │ IMAP FETCH    │               │               │
     │               │               │───────────────►│               │               │
     │               │               │               │               │               │
     │               │               │  Raw emails   │               │               │
     │               │               │◄───────────────│               │               │
     │               │               │               │               │               │
     │               │               │ For each email:               │               │
     │               │               │ 1. Parse MIME                 │               │
     │               │               │ 2. Check X-QuMail-* headers   │               │
     │               │               │ 3. Extract key_id             │               │
     │               │               │               │               │               │
     │               │               │ GET /keys/{key_id}            │               │
     │               │               │───────────────────────────────►│               │
     │               │               │               │               │               │
     │               │               │     {key_material}            │               │
     │               │               │◄───────────────────────────────│               │
     │               │               │               │               │               │
     │               │               │ decrypt(ciphertext, key)      │               │
     │               │               │───────────────────────────────────────────────►│
     │               │               │               │               │               │
     │               │               │        plaintext              │               │
     │               │               │◄───────────────────────────────────────────────│
     │               │               │               │               │               │
     │               │ {emails: [...]}               │               │               │
     │               │◄───────────────│               │               │               │
     │               │               │               │               │               │
     │  View emails  │               │               │               │               │
     │◄───────────────│               │               │               │               │
     │               │               │               │               │               │
```

---

## Threat Model

### Assumptions

| Assumption | Implication |
|------------|-------------|
| Network is hostile | All traffic can be intercepted; use TLS for all connections |
| Email servers are untrusted | Servers store only encrypted blobs; no plaintext ever transmitted |
| Attacker can read stored emails | Encryption must withstand offline attacks |
| Attacker cannot access KM | Key material is secure; KM is in a trusted zone |
| Local machine may be compromised | Minimize key exposure; use memory protection |

### Threat Matrix

| Threat | Attack Vector | Mitigation | Security Level Impact |
|--------|--------------|------------|----------------------|
| **T1: Network Eavesdropping** | Attacker intercepts email in transit | TLS + application-layer encryption | All levels protected (L1-L3) |
| **T2: Server Compromise** | Attacker gains access to email server | Only encrypted blobs stored | L1-L3: Protected, L4: Exposed |
| **T3: Key Theft** | Attacker steals encryption keys | Keys in memory only, encryption at rest, zeroization | L1: Perfect (OTP), L2-L3: Forward secrecy needed |
| **T4: Cryptanalysis** | Future quantum computer breaks encryption | L1: Information-theoretic security; L3: PQC resistant | L1, L3: Protected; L2: Vulnerable |
| **T5: Replay Attack** | Attacker replays old encrypted messages | Each email has unique key_id/nonce | All levels protected |
| **T6: Man-in-the-Middle** | Attacker intercepts frontend-backend | Backend binds to 127.0.0.1 only | Protected by localhost binding |
| **T7: Key Exhaustion** | Attacker forces key consumption | Policy engine monitors usage; alerts on anomaly | L1 affected; L2-L3 fallback available |

### Security Guarantees by Level

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Security Level Comparison                             │
├──────────────┬────────────────┬─────────────┬─────────────┬────────────────┤
│   Property   │    Level 1     │   Level 2   │   Level 3   │    Level 4     │
│              │     (OTP)      │   (AES)     │    (PQC)    │    (Plain)     │
├──────────────┼────────────────┼─────────────┼─────────────┼────────────────┤
│ Confidential │ ✓ Perfect      │ ✓ Strong    │ ✓ Strong    │ ✗ None         │
│ Integrity    │ ✓ (HMAC)       │ ✓ (GCM)     │ ✓ (Dilith)  │ ✗ None         │
│ Quantum-Safe │ ✓ Information  │ ✗ Vulnerable│ ✓ Algorithm │ ✗ N/A          │
│              │   theoretic    │   to QC     │   based     │                │
│ Key Reuse    │ ✗ Never        │ ✓ Yes       │ ✓ Yes       │ N/A            │
│ Scalability  │ ✗ Limited      │ ✓ High      │ ✓ Good      │ ✓ N/A          │
│ Deniability  │ ✗ No           │ ✗ No        │ ✗ No        │ ✗ No           │
└──────────────┴────────────────┴─────────────┴─────────────┴────────────────┘
```

---

## Phase 2 – API Specifications

### Backend API Contract (React ↔ Python)

> [!IMPORTANT]
> All API endpoints are protected by bearer tokens. The token is generated during initial launch and stored securely by Electron.

#### Authentication Endpoints

```yaml
POST /api/v1/auth/token
  Description: Generate session token for frontend-backend communication
  Request:
    - app_secret: string (generated by Electron)
  Response:
    - access_token: string
    - expires_in: integer (seconds)

POST /api/v1/auth/oauth/gmail/init
  Description: Initiate Gmail OAuth2 flow
  Response:
    - auth_url: string
    - state: string

POST /api/v1/auth/oauth/gmail/callback
  Description: Complete OAuth2 flow with authorization code
  Request:
    - code: string
    - state: string
  Response:
    - success: boolean
    - email: string
```

#### Email Endpoints

```yaml
GET /api/v1/emails
  Description: Fetch emails from inbox
  Query Parameters:
    - folder: string (INBOX, SENT, DRAFTS)
    - page: integer
    - limit: integer (max 50)
    - decrypt: boolean (default true)
  Response:
    - emails: array of EmailSummary
    - total: integer
    - has_more: boolean

GET /api/v1/emails/{message_id}
  Description: Get full email with decrypted content
  Response:
    - message_id: string
    - from: string
    - to: array of string
    - subject: string
    - body: string (decrypted)
    - attachments: array of AttachmentMeta
    - security_level: integer (1-4)
    - key_id: string (if encrypted)
    - received_at: datetime

POST /api/v1/emails/send
  Description: Compose and send encrypted email
  Request:
    - to: array of string
    - cc: array of string (optional)
    - subject: string
    - body: string (plaintext)
    - attachments: array of AttachmentUpload (optional)
    - security_level: integer (1-4)
    - recipient_key_id: string (optional, for PQC)
  Response:
    - success: boolean
    - message_id: string
    - key_id: string (if encrypted)
    - security_level_used: integer

POST /api/v1/emails/draft
  Description: Save email as draft
  Request: (same as send)
  Response:
    - draft_id: string

DELETE /api/v1/emails/{message_id}
  Description: Delete email
  Response:
    - success: boolean
```

#### Security Status Endpoints

```yaml
GET /api/v1/security/status
  Description: Get current security status
  Response:
    - km_connected: boolean
    - available_key_material: object
      - otp_bytes: integer
      - aes_keys: integer
    - pqc_keys_available: integer
    - last_key_sync: datetime

GET /api/v1/security/capabilities/{email}
  Description: Check recipient's QuMail capabilities
  Response:
    - is_qumail_user: boolean
    - supported_levels: array of integer
    - public_key: string (PQC public key, if available)

POST /api/v1/security/refresh-keys
  Description: Request new key material from KM
  Request:
    - key_type: string (otp, aes, pqc)
    - size: integer (bytes)
  Response:
    - success: boolean
    - keys_added: integer
```

### Key Manager REST API (ETSI GS QKD 014 Style)

```yaml
POST /api/v1/keys/request
  Description: Request new key material from QKD system
  Request:
    Headers:
      - Authorization: Bearer {km_token}
    Body:
      - peer_id: string (recipient identifier)
      - size: integer (bytes, max 1MB for OTP)
      - key_type: string (otp, aes_seed)
  Response:
    - key_id: string (UUID)
    - key_material: string (base64-encoded)
    - created_at: datetime
    - expires_at: datetime
    - peer_id: string
  Errors:
    - 503: Insufficient key material available

GET /api/v1/keys/{key_id}
  Description: Retrieve key material by ID
  Request:
    Headers:
      - Authorization: Bearer {km_token}
  Response:
    - key_id: string
    - key_material: string (base64-encoded)
    - key_type: string
    - used: boolean
    - peer_id: string
  Errors:
    - 404: Key not found
    - 410: Key already consumed (for OTP)

POST /api/v1/keys/{key_id}/consume
  Description: Mark key as consumed (required for OTP)
  Request:
    Headers:
      - Authorization: Bearer {km_token}
  Response:
    - success: boolean
    - consumed_at: datetime
  Errors:
    - 410: Key already consumed

GET /api/v1/keys/status
  Description: Get available key material status
  Request:
    Headers:
      - Authorization: Bearer {km_token}
    Query:
      - peer_id: string (optional)
  Response:
    - total_available_bytes: integer
    - peers: object
      - {peer_id}: 
          - available_bytes: integer
          - keys_count: integer

DELETE /api/v1/keys/{key_id}
  Description: Zeroize key (emergency revocation)
  Response:
    - success: boolean
    - zeroized_at: datetime
```

### Encrypted Email Wire Format

```
MIME-Version: 1.0
From: sender@gmail.com
To: recipient@gmail.com
Subject: [QuMail Encrypted] Meeting Tomorrow
Date: Mon, 13 Jan 2026 10:30:00 +0530
Content-Type: multipart/mixed; boundary="=_QuMail_Boundary_v1"
X-QuMail-Version: 1.0
X-QuMail-Security-Level: 2
X-QuMail-Key-ID: 550e8400-e29b-41d4-a716-446655440000
X-QuMail-Algorithm: AES-256-GCM
X-QuMail-Recipient-Fingerprint: SHA256:abc123...

--=_QuMail_Boundary_v1
Content-Type: application/x-qumail-envelope; charset=utf-8
Content-Transfer-Encoding: base64

eyJub25jZSI6ICJiYXNlNjRfbm9uY2UiLCAidGFnIjogImJhc2U2NF90YWciLCAi
Y2lwaGVydGV4dCI6ICJiYXNlNjRfZW5jcnlwdGVkX2JvZHkifQ==

--=_QuMail_Boundary_v1
Content-Type: application/x-qumail-attachment; name="document.pdf.enc"
Content-Transfer-Encoding: base64
X-QuMail-Original-Name: document.pdf
X-QuMail-Original-Size: 102400

W2VuY3J5cHRlZCBhdHRhY2htZW50IGRhdGFd...

--=_QuMail_Boundary_v1--
```

#### Envelope JSON Structure (base64-decoded):

```json
{
  "version": "1.0",
  "security_level": 2,
  "algorithm": "AES-256-GCM",
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "nonce": "base64_encoded_12_bytes",
  "tag": "base64_encoded_16_bytes",
  "ciphertext": "base64_encoded_encrypted_body",
  "attachments": [
    {
      "name": "document.pdf",
      "size": 102400,
      "nonce": "base64_nonce",
      "tag": "base64_tag",
      "content_ref": "inline" 
    }
  ],
  "timestamp": "2026-01-13T10:30:00Z",
  "sender_verification": "optional_dilithium_signature"
}
```

---

## Phase 3 – Implementation Structure

### Folder Structure

```
d:\QuMail\
├── README.md
├── LICENSE
├── .gitignore
├── docker-compose.yml              # For running KM separately
│
├── backend/                         # Python FastAPI backend
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── main.py                      # FastAPI application entry point
│   ├── config.py                    # Configuration management
│   │
│   ├── api/                         # API routes
│   │   ├── __init__.py
│   │   ├── auth.py                  # Authentication endpoints
│   │   ├── emails.py                # Email operations endpoints
│   │   ├── security.py              # Security status endpoints
│   │   └── dependencies.py          # FastAPI dependencies
│   │
│   ├── email_service/               # Email protocol handling
│   │   ├── __init__.py
│   │   ├── smtp_handler.py          # SMTP sending
│   │   ├── imap_handler.py          # IMAP receiving
│   │   ├── oauth2.py                # Gmail OAuth2 flow
│   │   ├── mime_builder.py          # Build encrypted MIME
│   │   └── mime_parser.py           # Parse encrypted MIME
│   │
│   ├── crypto_engine/               # Cryptographic operations
│   │   ├── __init__.py
│   │   ├── otp.py                   # One-Time Pad implementation
│   │   ├── aes_gcm.py               # AES-256-GCM encryption
│   │   ├── pqc.py                   # Post-quantum (Kyber/Dilithium)
│   │   ├── key_derivation.py        # HKDF and key stretching
│   │   └── secure_random.py         # Secure random generation
│   │
│   ├── qkd_client/                  # Key Manager client
│   │   ├── __init__.py
│   │   ├── client.py                # REST client for KM
│   │   ├── models.py                # KM response models
│   │   └── exceptions.py            # KM-specific exceptions
│   │
│   ├── key_store/                   # Key management
│   │   ├── __init__.py
│   │   ├── memory_store.py          # In-memory key storage
│   │   ├── encrypted_store.py       # Encrypted disk storage
│   │   └── lifecycle.py             # Key lifecycle management
│   │
│   ├── policy_engine/               # Security policy enforcement
│   │   ├── __init__.py
│   │   ├── validator.py             # Request validation
│   │   ├── rules.py                 # Security rules
│   │   └── fallback.py              # Degradation handling
│   │
│   ├── storage/                     # Persistent storage
│   │   ├── __init__.py
│   │   ├── database.py              # SQLite management
│   │   ├── models.py                # SQLAlchemy models
│   │   └── audit.py                 # Audit logging
│   │
│   └── tests/                       # Backend tests
│       ├── __init__.py
│       ├── test_crypto.py
│       ├── test_email.py
│       └── test_integration.py
│
├── key_manager/                     # Simulated QKD Key Manager
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── main.py                      # KM FastAPI entry point
│   ├── config.py
│   │
│   ├── api/                         # KM REST API
│   │   ├── __init__.py
│   │   ├── keys.py                  # Key endpoints
│   │   └── status.py                # Status endpoints
│   │
│   ├── core/                        # KM core logic
│   │   ├── __init__.py
│   │   ├── key_generator.py         # Key generation (simulated QKD)
│   │   ├── key_pool.py              # Key pool management
│   │   ├── peer_manager.py          # Peer provisioning
│   │   └── lifecycle.py             # Key lifecycle (OTP enforcement)
│   │
│   └── tests/
│       └── test_km.py
│
├── frontend/                        # React TypeScript frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   │
│   ├── src/
│   │   ├── main.tsx                 # React entry point
│   │   ├── App.tsx                  # Main application component
│   │   │
│   │   ├── components/              # React components
│   │   │   ├── Layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Layout.tsx
│   │   │   │
│   │   │   ├── Email/
│   │   │   │   ├── EmailList.tsx
│   │   │   │   ├── EmailView.tsx
│   │   │   │   ├── ComposeEmail.tsx
│   │   │   │   └── AttachmentList.tsx
│   │   │   │
│   │   │   ├── Security/
│   │   │   │   ├── SecurityLevelSelector.tsx
│   │   │   │   ├── SecurityBadge.tsx
│   │   │   │   └── KeyStatusIndicator.tsx
│   │   │   │
│   │   │   ├── Auth/
│   │   │   │   ├── LoginScreen.tsx
│   │   │   │   └── OAuthCallback.tsx
│   │   │   │
│   │   │   └── Common/
│   │   │       ├── Button.tsx
│   │   │       ├── Input.tsx
│   │   │       ├── Modal.tsx
│   │   │       └── Loading.tsx
│   │   │
│   │   ├── api/                     # API client layer
│   │   │   ├── client.ts            # Base API client
│   │   │   ├── auth.ts              # Auth API calls
│   │   │   ├── emails.ts            # Email API calls
│   │   │   └── security.ts          # Security API calls
│   │   │
│   │   ├── hooks/                   # React hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useEmails.ts
│   │   │   └── useSecurityStatus.ts
│   │   │
│   │   ├── types/                   # TypeScript types
│   │   │   ├── email.ts
│   │   │   ├── security.ts
│   │   │   └── api.ts
│   │   │
│   │   └── styles/                  # CSS styles
│   │       ├── index.css
│   │       ├── variables.css
│   │       └── components/
│   │
│   └── public/
│       └── icons/
│
├── electron/                        # Electron shell
│   ├── package.json
│   ├── electron-builder.yml
│   │
│   ├── src/
│   │   ├── main.ts                  # Main process
│   │   ├── preload.ts               # Preload script (IPC bridge)
│   │   ├── backend-manager.ts       # Python backend lifecycle
│   │   └── ipc-handlers.ts          # IPC message handlers
│   │
│   └── resources/
│       └── icon.ico
│
└── docs/                            # Documentation
    ├── architecture.md
    ├── api-reference.md
    ├── security-model.md
    ├── threat-model.md
    └── deployment.md
```

---

## Phase 4 – Security Implementation Details

### Level 1: One-Time Pad (OTP)

```
┌─────────────────────────────────────────────────────────────────┐
│                     OTP Encryption Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Plaintext:  H  E  L  L  O     (72, 69, 76, 76, 79)             │
│              ↓  ↓  ↓  ↓  ↓                                       │
│  Key:        K1 K2 K3 K4 K5    (random bytes from QKD)          │
│              ↓  ↓  ↓  ↓  ↓                                       │
│         XOR ⊕⊕⊕⊕⊕                                                │
│              ↓  ↓  ↓  ↓  ↓                                       │
│  Ciphertext: C1 C2 C3 C4 C5    (transmitted via email)          │
│                                                                  │
│  Constraints:                                                    │
│  • len(key) == len(plaintext)                                   │
│  • Key MUST be truly random (from QKD)                          │
│  • Key MUST be used exactly once                                │
│  • Key MUST be securely destroyed after use                     │
│                                                                  │
│  Security Property: Information-theoretic security              │
│  (unbreakable even with infinite computational power)           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**OTP Enforcement Logic:**
1. Before encryption: Request key of exact message length from KM
2. KM marks key as "reserved" with TTL
3. After successful send: Call `/keys/{key_id}/consume` to mark used
4. KM permanently marks key as consumed, prevents any future retrieval
5. Backend zeroizes local key copy from memory

### Level 2: Quantum-Aided AES-256-GCM

```
┌─────────────────────────────────────────────────────────────────┐
│                   AES-GCM Encryption Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  QKD Key (32 bytes) ────┐                                        │
│                         │                                        │
│                         ▼                                        │
│              ┌─────────────────┐                                 │
│              │      HKDF       │  (key derivation)               │
│              │  context: email │                                 │
│              └────────┬────────┘                                 │
│                       │                                          │
│           ┌───────────┼───────────┐                              │
│           ▼           ▼           ▼                              │
│     Encryption    MAC Key      Nonce                             │
│        Key                   (random 12B)                        │
│      (32 bytes)                                                  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────┐                 │
│  │              AES-256-GCM                     │                 │
│  │  Plaintext ──► Ciphertext + Authentication  │                 │
│  │                          Tag (16 bytes)     │                 │
│  └─────────────────────────────────────────────┘                 │
│                                                                  │
│  Output: {nonce, ciphertext, tag}                                │
│                                                                  │
│  Security Property: Quantum-derived randomness                   │
│  enhances key unpredictability                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Level 3: Post-Quantum Cryptography (Kyber + Dilithium)

```
┌─────────────────────────────────────────────────────────────────┐
│                     PQC Hybrid Flow                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Sender                              Recipient                   │
│  ────────                            ─────────                   │
│                                                                  │
│  1. Get recipient's Kyber public key (from directory/email)     │
│                                                                  │
│  2. Kyber Key Encapsulation:                                     │
│     ┌─────────────────────────────────────────┐                  │
│     │ (ciphertext, shared_secret) =           │                  │
│     │     Kyber.Encapsulate(recipient_pk)     │                  │
│     └─────────────────────────────────────────┘                  │
│                                                                  │
│  3. Derive AES key from shared_secret + QKD material:            │
│     aes_key = HKDF(shared_secret || qkd_key)                    │
│                                                                  │
│  4. Encrypt message with AES-GCM:                                │
│     encrypted = AES_GCM_Encrypt(aes_key, plaintext)             │
│                                                                  │
│  5. (Optional) Sign with Dilithium:                              │
│     signature = Dilithium.Sign(sender_sk, encrypted)            │
│                                                                  │
│  6. Send: {kyber_ciphertext, aes_encrypted, signature}          │
│                                                                  │
│  ──────────────────────────────────────────────────────────────  │
│                                                                  │
│  Recipient decapsulates to recover shared_secret,                │
│  derives AES key, decrypts message, verifies signature           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Lifecycle State Machine

```
┌──────────────────────────────────────────────────────────────────┐
│                     Key Lifecycle States                          │
└──────────────────────────────────────────────────────────────────┘

                    ┌─────────────┐
                    │ PROVISIONED │  (Key generated in KM)
                    └──────┬──────┘
                           │
                    Request key
                           │
                           ▼
                    ┌─────────────┐
                    │  RESERVED   │  (Key assigned to transaction)
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        Use completed              Timeout/Cancel
              │                         │
              ▼                         ▼
       ┌─────────────┐           ┌─────────────┐
       │  CONSUMED   │           │  RELEASED   │
       │  (OTP only) │           │             │
       └──────┬──────┘           └──────┬──────┘
              │                         │
              │                   Back to pool
              │                         │
              ▼                         ▼
       ┌─────────────┐           ┌─────────────┐
       │  ZEROIZED   │           │ PROVISIONED │
       │  (Deleted)  │           │             │
       └─────────────┘           └─────────────┘


OTP Mode: PROVISIONED → RESERVED → CONSUMED → ZEROIZED (no reuse)
AES Mode: PROVISIONED → RESERVED → USED → (can remain for decrypt)
PQC Mode: Long-term keys with periodic rotation
```

---

## Phase 5 – Demo & Extension

### Extension to Chat/Audio/Video

```
┌─────────────────────────────────────────────────────────────────┐
│             Future Extension Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current: Email Only                                             │
│  ┌────────────┐                                                  │
│  │   Email    │ ◄──── Crypto Engine ◄──── Key Store              │
│  │  Service   │                                                  │
│  └────────────┘                                                  │
│                                                                  │
│  Extended: Unified Secure Communication                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                   │
│  │   Email    │ │    Chat    │ │   Media    │                   │
│  │  Service   │ │  Service   │ │  Service   │                   │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                   │
│        │              │              │                           │
│        └──────────────┼──────────────┘                           │
│                       ▼                                          │
│              ┌─────────────────┐                                 │
│              │  Unified Crypto │  (shared crypto engine)         │
│              │     Engine      │                                 │
│              └────────┬────────┘                                 │
│                       │                                          │
│              ┌────────┴────────┐                                 │
│              ▼                 ▼                                 │
│       ┌───────────┐    ┌────────────┐                           │
│       │ Key Store │    │ QKD Client │                           │
│       │           │    │            │                           │
│       └───────────┘    └────────────┘                           │
│                                                                  │
│  Chat Extension:                                                 │
│  • WebSocket-based real-time messaging                          │
│  • Per-message encryption with session keys                     │
│  • Forward secrecy via key ratcheting                           │
│                                                                  │
│  Audio/Video Extension:                                          │
│  • WebRTC with custom encryption layer                          │
│  • SRTP with QKD-derived keys                                   │
│  • Continuous key refresh during session                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Known Limitations

| Limitation | Reason | Future Improvement |
|------------|--------|-------------------|
| Simulated KM | Real QKD requires specialized hardware | Integrate with commercial QKD systems |
| Single device | Key material not synchronized across devices | Implement secure key synchronization |
| Gmail OAuth only | Time constraint | Add Yahoo, Outlook OAuth |
| No key escrow | Privacy-first design | Optional organizational key recovery |
| Local only | Desktop application | Cloud-sync with zero-knowledge encryption |

---

## Verification Plan

### Automated Tests

1. **Unit Tests**: All crypto operations tested with known test vectors
2. **Integration Tests**: Full email send/receive cycle
3. **Security Tests**: Key exhaustion, OTP reuse prevention, timing attacks

### Manual Verification

1. Send encrypted email between two QuMail instances
2. Verify email is unreadable in Gmail web interface
3. Confirm correct security level badge in UI
4. Test OTP mode with insufficient key material (should fail gracefully)

---

## User Review Required

> [!IMPORTANT]
> **Decision Point**: Before proceeding to implementation, please confirm:
> 1. Is the overall architecture acceptable?
> 2. Should I proceed with Electron or prefer Tauri for the desktop shell?
> 3. Any specific Gmail account to test OAuth2 flow?
> 4. Is the simulated KM running on the same machine acceptable, or should it be a separate container?
