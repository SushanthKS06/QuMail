# QuMail Security Data Flow Diagrams

This document outlines the exact data flow between components during the encryption (Sending) and decryption (Receiving) processes for all three QuMail security levels.

## Level 1: Quantum Secure OTP
The purest form of encryption. Data flows straight from the QKD Key Manager directly into a bitwise XOR operation against the plaintext.

### Sender (Encryption) Flow
```mermaid
flowchart TD
    %% Components
    PT[Plaintext Email]
    KM[Key Manager :8100]
    API[QuMail Backend API]
    XOR{XOR Engine ⊕}
    MIME[MIME Builder]
    SMTP[SMTP Server]
    
    %% Data Flow
    PT -->|1. Raw Text String| API
    API -->|2. Request OTP bytes = len(text)| KM
    KM -->|3. Returns: raw_bytes + key_id| API
    
    API -->|4. plaintext_bytes| XOR
    API -->|5. raw_bytes| XOR
    
    XOR -->|6. Ciphertext_bytes| MIME
    API -->|7. key_id, L1 headers| MIME
    
    MIME -->|8. Base64 JSON Envelope| SMTP
    
    %% Styling
    style XOR fill:#e94560,color:#fff
    style KM fill:#0f3460,color:#fff
```

### Receiver (Decryption) Flow
```mermaid
flowchart TD
    %% Components
    IMAP[IMAP Server]
    MIME[MIME Parser]
    API[QuMail Backend API]
    KM[Key Manager :8100]
    XOR{XOR Engine ⊕}
    UI[QuMail Frontend UI]
    
    %% Data Flow
    IMAP -->|1. Base64 JSON Envelope| MIME
    MIME -->|2. Extracts: key_id| API
    MIME -->|3. Extracts: Ciphertext_bytes| XOR
    
    API -->|4. Request exact key_id| KM
    KM -->|5. Returns: matching raw_bytes| API
    API -->|6. raw_bytes| XOR
    
    XOR -->|7. Decoded plaintext_bytes| UI
    
    %% Styling
    style XOR fill:#e94560,color:#fff
    style KM fill:#0f3460,color:#fff
```

## Level 2: Quantum-Aided AES
The standard mode. Data flows from the Key Manager into an HKDF to derive a clean session key, which is then fed into the AES-GCM block cipher.

### Sender (Encryption) Flow
```mermaid
flowchart TD
    %% Components
    PT[Plaintext Email]
    KM[Key Manager]
    HKDF{HKDF Function}
    RNG{OS Randomizer}
    AES{AES-256-GCM Engine}
    MIME[MIME Builder]
    SMTP[SMTP Server]
    
    %% Data Flow
    PT -->|1. Raw Text String| AES
    
    KM -->|2. Returns: 32-byte QKD Seed + key_id| HKDF
    HKDF -->|3. Derives clean 256-bit Key| AES
    
    RNG -->|4. Generates 12-byte Nonce| AES
    
    AES -->|5. Outputs: Ciphertext| MIME
    AES -->|6. Outputs: 16-byte Auth Tag| MIME
    RNG -->|7. Forwards Nonce| MIME
    KM -->|8. Forwards key_id| MIME
    
    MIME -->|9. Packages Envelope| SMTP
    
    %% Styling
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```

### Receiver (Decryption) Flow
```mermaid
flowchart TD
    %% Components
    IMAP[IMAP Server]
    MIME[MIME Parser]
    KM[Key Manager]
    HKDF{HKDF Function}
    AES{AES-256-GCM Engine}
    UI[QuMail Frontend UI]
    ERR[Auth Error Handler]
    
    %% Data Flow
    IMAP -->|1. Base64 Envelope| MIME
    
    MIME -->|2. Extracts: key_id| KM
    KM -->|3. Returns: exact 32-byte QKD Seed| HKDF
    HKDF -->|4. Rebuilds 256-bit Key| AES
    
    MIME -->|5. Extracts: Ciphertext| AES
    MIME -->|6. Extracts: Nonce| AES
    MIME -->|7. Extracts: Auth Tag| AES
    
    AES -->|8a. Tag Verifies -> Plaintext| UI
    AES -->|8b. Tag Fails -> Abort| ERR
    
    %% Styling
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```

## Level 3: Post-Quantum Crypto (Hybrid)
The most complex flow. It combines a lattice-based Key Encapsulation Mechanism (Kyber) with QKD material to create a double-layered hybrid key.

### Sender (Encryption) Flow
```mermaid
flowchart TD
    %% Components
    PT[Plaintext Email]
    PUB[Alice's Kyber Public Key]
    KYB{Kyber.Encapsulate}
    KM[Key Manager]
    HKDF{Hybrid HKDF}
    AES{AES-256-GCM Engine}
    MIME[MIME Builder]
    SMTP[SMTP Server]
    
    %% Data Flow
    PUB -->|1. Input to Kyber| KYB
    KYB -->|2. Generates Shared Secret| HKDF
    KYB -->|3. Generates Kyber Ciphertext| MIME
    
    KM -->|4. Provides 32-byte QKD Seed + key_id| HKDF
    
    HKDF -->|5. Mixes Secret + Seed = Ultimate Key| AES
    
    PT -->|6. Raw Text String| AES
    AES -->|7. Outputs: AES Ciphertext + Nonce + Tag| MIME
    
    KM -->|8. Forwards qkd_key_id| MIME
    
    MIME -->|9. Packages double-layered Envelope| SMTP
    
    %% Styling
    style KYB fill:#4b1d52,color:#fff
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```

### Receiver (Decryption) Flow
```mermaid
flowchart TD
    %% Components
    IMAP[IMAP Server]
    MIME[MIME Parser]
    PRIV[Alice's Kyber Private Key]
    KYB{Kyber.Decapsulate}
    KM[Key Manager]
    HKDF{Hybrid HKDF}
    AES{AES-256-GCM Engine}
    UI[QuMail Frontend UI]
    
    %% Data Flow
    IMAP -->|1. Base64 Envelope| MIME
    
    MIME -->|2. Extracts Kyber Ciphertext| KYB
    PRIV -->|3. Input to solve puzzle| KYB
    KYB -->|4. Recovers exact Shared Secret| HKDF
    
    MIME -->|5. Extracts qkd_key_id| KM
    KM -->|6. Returns exact 32-byte QKD Seed| HKDF
    
    HKDF -->|7. Mixes Secret + Seed = Ultimate Key| AES
    
    MIME -->|8. Extracts AES Ciphertext + Nonce + Tag| AES
    
    AES -->|9. Tag Verifies -> Plaintext| UI
    
    %% Styling
    style KYB fill:#4b1d52,color:#fff
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```
