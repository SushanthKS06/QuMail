# QuMail - Quantum Secure Email Client

A production-grade Windows desktop email client with quantum-secure encryption, built as a modular and extensible system.

![Security Levels](https://img.shields.io/badge/Security_Levels-4-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-18-61dafb)
![Electron](https://img.shields.io/badge/Electron-28-47848f)

## Features

-  **Level 1: Quantum Secure OTP** - Information-theoretic security with One-Time Pad
-  **Level 2: Quantum-Aided AES** - AES-256-GCM with QKD-derived keys (default)
-  **Level 3: Post-Quantum Crypto** - Kyber + Dilithium for future-proof security
-  **Level 4: No Security** - Plain email for compatibility
-  **Simulated QKD Key Manager** - ETSI GS QKD 014 compliant REST API
-  **Gmail Integration** - Full OAuth2 authentication
-  **Windows Desktop App** - Electron-based native experience

##  Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Electron Desktop Shell                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              React Frontend (TypeScript)                   │  │
│  │   • Email List/View/Compose                               │  │
│  │   • Security Level Selector                               │  │
│  │   • Dark Theme UI                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Python FastAPI Backend (localhost:8000)            │
│                                                                  │
│  • Crypto Engine (OTP, AES-GCM, PQC)                            │
│  • Email Service (SMTP/IMAP/OAuth2)                             │
│  • Key Store (memory + encrypted disk)                          │
│  • Policy Engine (validation, fallback)                         │
│  • Storage (SQLite)                                             │
└─────────────────────────────────────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           Simulated QKD Key Manager (localhost:8100)             │
│                                                                  │
│  • ETSI GS QKD 014 API                                          │
│  • Key Pool Management                                          │
│  • One-Time Usage Enforcement                                   │
└─────────────────────────────────────────────────────────────────┘
```

##  Quick Start

The recommended way to run QuMail is using Docker for backend services and running the Electron app natively.

### 1. Start Backend Services (Docker)

Ensure Docker Desktop is running, then use Docker Compose:

```bash
git clone https://github.com/your-repo/qumail.git
cd qumail
docker-compose up -d --build
```
*Note: Building takes a few minutes as it compiles post-quantum libraries (`liboqs`) from source.*

### 2. Run the Desktop App

In a new terminal, start the Electron frontend:

```bash
cd electron
npm install
# PowerShell
$env:QUMAIL_USE_DOCKER="1"; npm run dev
# Bash
QUMAIL_USE_DOCKER=1 npm run dev
```

For detailed setup or troubleshooting, see the [Docker Setup Guide](docs/docker-setup.md).

> **Alternative**: If you want to run everything locally without Docker, you will need to manually start the `key_manager`, `backend`, and `frontend` separately. See our detailed documentation for manual run instructions.

##  Project Structure

```
QuMail/
├── README.md
├── .gitignore
│
├── backend/                    # Python FastAPI Backend
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   │
│   ├── api/                    # REST API routes
│   │   ├── auth.py             # Authentication & OAuth2
│   │   ├── emails.py           # Email CRUD operations
│   │   ├── security.py         # Security status & keys
│   │   └── dependencies.py     # FastAPI dependencies
│   │
│   ├── crypto_engine/          # Cryptographic operations
│   │   ├── __init__.py         # Main encrypt/decrypt
│   │   ├── otp.py              # One-Time Pad
│   │   ├── aes_gcm.py          # AES-256-GCM
│   │   ├── pqc.py              # Kyber + Dilithium
│   │   ├── key_derivation.py   # HKDF
│   │   └── secure_random.py    # CSPRNG utilities
│   │
│   ├── qkd_client/             # Key Manager client
│   │   ├── client.py           # REST client
│   │   ├── models.py           # Data models
│   │   └── exceptions.py       # Error types
│   │
│   ├── email_service/          # Email protocol handling
│   │   ├── smtp_handler.py     # Send emails
│   │   ├── imap_handler.py     # Fetch emails
│   │   ├── oauth2.py           # Token management
│   │   ├── mime_builder.py     # Build encrypted MIME
│   │   └── mime_parser.py      # Parse encrypted MIME
│   │
│   ├── key_store/              # Key management
│   │   ├── memory_store.py     # In-memory storage
│   │   ├── encrypted_store.py  # Disk storage
│   │   └── lifecycle.py        # State tracking
│   │
│   ├── policy_engine/          # Security policies
│   │   ├── validator.py        # Request validation
│   │   ├── rules.py            # Security rules
│   │   └── fallback.py         # Degradation logic
│   │
│   └── storage/                # Persistence
│       └── database.py         # SQLite operations
│
├── key_manager/                # Simulated QKD Key Manager
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration
│   │
│   ├── api/                    # REST API
│   │   ├── keys.py             # Key operations
│   │   └── status.py           # Status endpoints
│   │
│   └── core/                   # Core logic
│       └── key_pool.py         # Key pool management
│
├── frontend/                   # React TypeScript Frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx            # Entry point
│       ├── App.tsx             # Root component
│       │
│       ├── api/                # API clients
│       │   ├── client.ts       # Base client
│       │   ├── auth.ts         # Auth API
│       │   ├── emails.ts       # Email API
│       │   └── security.ts     # Security API
│       │
│       ├── components/         # React components
│       │   ├── Layout/         # App layout
│       │   ├── Email/          # Email components
│       │   ├── Security/       # Security UI
│       │   └── Auth/           # Login screen
│       │
│       ├── hooks/              # React hooks
│       │   ├── useAuth.ts
│       │   ├── useEmails.ts
│       │   └── useSecurityStatus.ts
│       │
│       ├── types/              # TypeScript types
│       │   ├── email.ts
│       │   └── api.ts
│       │
│       └── styles/             # CSS styles
│           └── index.css
│
├── electron/                   # Electron Desktop Shell
│   ├── package.json
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── main.ts             # Main process
│       ├── preload.ts          # IPC bridge
│       ├── backend-manager.ts  # Python lifecycle
│       └── ipc-handlers.ts     # IPC handlers
│
└── docs/                       # Documentation
    ├── architecture.md
    ├── api-reference.md
    └── security-model.md
```

##  Security Levels

| Level | Name | Algorithm | Quantum-Safe | Use Case |
|-------|------|-----------|--------------|----------|
| 1 | Quantum Secure OTP | XOR with QKD key |  Perfect | Highest sensitivity |
| 2 | Quantum-Aided AES | AES-256-GCM | Ⅹ | Standard secure email |
| 3 | Post-Quantum Crypto | Kyber-768 + AES | ✓| Long-term confidentiality |
| 4 | No Security | None | N/A | Compatibility |

##  Important Notes

### Simulation Notice
The Key Manager is a **simulation** using cryptographically secure random numbers (CSPRNG). In production, this would interface with real QKD hardware.

### Security Constraints
- Backend binds to `127.0.0.1` only (no network exposure)
- Keys never touch disk unless encrypted
- All cryptography happens in the backend (never in frontend)
- One-time keys are immediately consumed and zeroized

##  Documentation

- [Docker Setup Guide](docs/docker-setup.md) - Instructions for running with Docker
- [Architecture](docs/architecture.md) - System design and components
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Security Model](docs/security-model.md) - Encryption details and threat model

##  Development

### Backend Development
```bash
cd backend
pip install -e ".[dev]"
python main.py
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Run Tests
```bash
cd backend
pytest tests/
```

##  License

MIT License - See [LICENSE](LICENSE) for details.

##  Acknowledgments

- ETSI GS QKD 014 for Key Manager API specification
- NIST for post-quantum algorithm standards (Kyber, Dilithium)
- Open Quantum Safe (liboqs) for PQC implementations


