# QuMail System Architecture

## Overview

QuMail is a quantum-secure email client that provides end-to-end encryption using QKD-derived keys. This document details the system architecture and security model.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Electron Desktop Shell                             │
│                    (Window management, Process lifecycle)                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     React Frontend (TypeScript)                          ││
│  │   ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────────┐   ││
│  │   │   Inbox     │ │   Compose   │ │   Security Level Selector       │   ││
│  │   │   View      │ │   Email     │ │   [🔐][🛡️][⚛️][📧]              │   ││
│  │   └─────────────┘ └─────────────┘ └─────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                          REST API (localhost:8000)
                          Bearer Token Authentication
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Python FastAPI Backend                                  │
│                 (Security Core - All crypto here)                           │
│                                                                              │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────────┐ │
│  │ Email Service │ │ Crypto Engine │ │  QKD Client   │ │ Policy Engine   │ │
│  │               │ │               │ │               │ │                 │ │
│  │ • SMTP        │ │ • OTP         │ │ • Key Request │ │ • Validation    │ │
│  │ • IMAP        │ │ • AES-GCM     │ │ • Key Fetch   │ │ • Fallback      │ │
│  │ • OAuth2      │ │ • PQC         │ │ • Consume     │ │ • Audit         │ │
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────────────┘ │
│                                                                              │
│  ┌───────────────────────────────────┐ ┌──────────────────────────────────┐│
│  │          Key Store                 │ │          Storage                 ││
│  │  • In-memory (zeroizable)          │ │  • SQLite (encrypted)           ││
│  │  • Encrypted disk cache            │ │  • OAuth tokens                 ││
│  │  • Lifecycle tracking              │ │  • Audit logs                   ││
│  └───────────────────────────────────┘ └──────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                          REST API (localhost:8100)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              Simulated QKD Key Manager (ETSI GS QKD 014)                     │
│                                                                              │
│  • Key generation (CSPRNG simulation)                                        │
│  • Key pool management                                                       │
│  • One-time usage enforcement                                                │
│  • ETSI-compliant REST API                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Security Levels

### Level 1: Quantum Secure OTP
- **Algorithm**: XOR with key equal to message length
- **Key Source**: QKD Key Manager
- **Security**: Information-theoretic (unbreakable)
- **Constraint**: Key length == message length, one-time use
- **Use Case**: Highest sensitivity communications

### Level 2: Quantum-Aided AES (Default)
- **Algorithm**: AES-256-GCM
- **Key Source**: QKD-derived via HKDF
- **Security**: Computationally secure
- **Constraint**: 32-byte key per message
- **Use Case**: Standard secure email

### Level 3: Post-Quantum Crypto
- **Algorithm**: Kyber-768 (KEM) + AES-256-GCM
- **Key Source**: Kyber encapsulation + QKD
- **Security**: Quantum-resistant (lattice-based)
- **Constraint**: Recipient public key required
- **Use Case**: Long-term confidentiality

### Level 4: No Security
- **Algorithm**: None (plain text)
- **Key Source**: N/A
- **Security**: None
- **Use Case**: Compatibility with non-QuMail users

## Threat Model

| Threat | Mitigation |
|--------|------------|
| Network eavesdropping | TLS + application-layer encryption |
| Email server compromise | Only encrypted blobs stored |
| Key theft | Memory-only storage, zeroization |
| Quantum computing | Level 1 (OTP) and Level 3 (PQC) |
| Replay attacks | Unique key_id per message |
| Man-in-the-middle | Localhost-only backend binding |

## Component Responsibilities

### Frontend (React)
- UI rendering only
- NO cryptographic operations
- NO key storage
- NO direct protocol access

### Backend (Python)
- ALL cryptographic operations
- Email protocol handling
- Key lifecycle management
- Policy enforcement

### Key Manager (Simulated)
- Key generation and storage
- Key allocation to peers
- One-time usage enforcement
- ETSI QKD 014 API
