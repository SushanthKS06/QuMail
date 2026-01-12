# QuMail Security Model

## Overview

QuMail provides quantum-secure email encryption through application-layer security. Email servers never see plaintext content - they only store and transmit encrypted blobs.

## Security Principles

### 1. Defense in Depth
- Multiple encryption layers
- TLS for transport
- Application-layer encryption for content
- Key material from QKD

### 2. Zero Trust
- Assume network is hostile
- Assume email servers are compromised
- Trust only the local application and Key Manager

### 3. Separation of Concerns
- Cryptography isolated in backend
- Frontend handles UI only
- Key Manager handles key lifecycle

### 4. Minimal Key Exposure
- Keys in memory only where possible
- Automatic zeroization after use
- No key logging

## Encryption Details

### One-Time Pad (Level 1)

```
Plaintext:  [72, 69, 76, 76, 79]  (H, E, L, L, O)
Key:        [45, 92, 13, 88, 41]  (random from QKD)
            ─────────────────────
XOR:        [117, 25, 65, 28, 102] (ciphertext)
```

**Requirements:**
- `len(key) >= len(plaintext)`
- Key is truly random (from QKD)
- Key is used exactly once
- Key is destroyed after use

**Security Proof:**
For any ciphertext C, any plaintext P is equally likely given:
- `K = C ⊕ P` is a valid random key
- Each P maps to a unique K
- All K are equally probable

### AES-256-GCM (Level 2)

```
QKD Key (32 bytes)
       │
       ▼
    ┌──────┐
    │ HKDF │ ─────► Encryption Key (32 bytes)
    └──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│              AES-256-GCM                │
│  Plaintext + Nonce ──► Ciphertext + Tag │
└─────────────────────────────────────────┘
```

**Components:**
- **Key**: 256-bit from HKDF(QKD material)
- **Nonce**: 12-byte random
- **Tag**: 16-byte authentication

**Security Properties:**
- Confidentiality: AES-256 block cipher
- Integrity: GCM authentication tag
- Authenticity: Tag verification

### Post-Quantum Crypto (Level 3)

```
Sender                              Recipient
──────                              ─────────
                                    
   ┌──────────────────────────────────┐
   │ 1. Get recipient's Kyber public key
   └──────────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ 2. Kyber.Encapsulate(pk)         │
   │    → (ciphertext, shared_secret) │
   └──────────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ 3. HKDF(shared_secret || qkd_key)│
   │    → aes_key                     │
   └──────────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ 4. AES-GCM.Encrypt(aes_key, msg) │
   └──────────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ 5. Send: kyber_ct + aes_ct + tag │
   └──────────────────────────────────┘
```

**Algorithms:**
- **KEM**: Kyber-768 (NIST standard)
- **Signature**: Dilithium3 (optional)
- **Symmetric**: AES-256-GCM

## Key Lifecycle

```
    ┌─────────────┐
    │ PROVISIONED │ ◄── Key generated in KM
    └──────┬──────┘
           │ Request
           ▼
    ┌─────────────┐
    │   RESERVED  │ ◄── Key assigned to transaction
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │           │
  Success     Timeout
     │           │
     ▼           ▼
┌─────────┐ ┌───────────┐
│CONSUMED │ │ RELEASED  │
│(OTP)    │ │           │
└────┬────┘ └─────┬─────┘
     │            │
     ▼            │
┌─────────┐       │
│ZEROIZED │       │
└─────────┘       │
                  ▼
           ┌───────────┐
           │PROVISIONED│ (back to pool)
           └───────────┘
```

## Threat Matrix

| Threat | Vector | Mitigation | Level Protection |
|--------|--------|------------|------------------|
| **T1: Eavesdropping** | Network intercept | TLS + app encryption | All (1-3) |
| **T2: Server Breach** | Access stored emails | Only encrypted blobs | All (1-3) |
| **T3: Key Theft** | Memory dump | Zeroization, memory protection | L1 best |
| **T4: Quantum Attack** | Future QC | L1 (OTP), L3 (PQC) | L1, L3 |
| **T5: Replay** | Re-send old email | Unique key_id/nonce | All |
| **T6: MITM** | Frontend-backend | Localhost binding | All |

## Wire Format

Encrypted emails use this MIME structure:

```
MIME-Version: 1.0
From: sender@gmail.com
To: recipient@gmail.com
Subject: [QuMail Encrypted] Meeting
X-QuMail-Version: 1.0
X-QuMail-Security-Level: 2
X-QuMail-Key-ID: 550e8400-...
X-QuMail-Algorithm: AES-256-GCM

--=_QuMail_Boundary_v1
Content-Type: application/x-qumail-envelope

{BASE64_ENCRYPTED_ENVELOPE}

--=_QuMail_Boundary_v1--
```

**Envelope JSON (base64-decoded):**
```json
{
  "version": "1.0",
  "security_level": 2,
  "algorithm": "AES-256-GCM",
  "key_id": "550e8400-...",
  "nonce": "base64_12_bytes",
  "tag": "base64_16_bytes",
  "ciphertext": "base64_encrypted_body"
}
```

## Security Guarantees by Level

| Property | L1 (OTP) | L2 (AES) | L3 (PQC) | L4 (None) |
|----------|----------|----------|----------|-----------|
| Confidentiality | Perfect | Strong | Strong | None |
| Integrity | HMAC | GCM | Dilithium | None |
| Quantum-Safe | ✓ (info-theoretic) | ✗ | ✓ (algorithm) | N/A |
| Key Reuse | Never | Possible | Possible | N/A |
| Scalability | Limited | High | Good | N/A |

## Simulation Notice

 **The Key Manager is a SIMULATION**

In this implementation:
- Keys are generated using CSPRNG (os.urandom)
- No actual quantum hardware is involved
- No real peer-to-peer key distribution

In production QKD:
- Keys come from quantum random number generators
- Keys are distributed via quantum channels (fiber optic)
- Key rates depend on link quality and distance
