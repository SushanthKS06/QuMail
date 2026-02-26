# QuMail Security Visual Diagrams

This document contains both Data Flow Diagrams and Use Case Diagrams for the QuMail security architecture.

## 1. Use Case Diagrams

Use Case diagrams show the interactions between Actors (users or external systems) and the QuMail system.

### Sender Use Cases
```mermaid
flowchart LR
    %% Actors
    Sender((Email Sender))
    Gmail[[Gmail / SMTP Server]]
    QKD[[Simulated QKD Network]]

    %% System Boundary
    subgraph QuMail System
        Compose([Compose Email])
        SelectLvl([Select Security Level])
        ReqKey([Request Encryption Key])
        Encrypt([Encrypt Email Content])
        PackMIME([Package as Secure MIME])
        Dispatch([Send via External Mail])
    end

    %% Relationships
    Sender --> Compose
    Sender --> SelectLvl
    Compose -.->|"includes"| Encrypt
    SelectLvl -.->|"determines"| Encrypt
    
    Encrypt -.->|"includes"| ReqKey
    ReqKey --> QKD
    
    Encrypt -.->|"outputs"| PackMIME
    PackMIME -.->|"forwards to"| Dispatch
    Dispatch --> Gmail
    
    %% Styling
    style Gmail fill:#2d2d44,stroke:#ff6b6b,color:#fff
    style QKD fill:#1a1a2e,stroke:#0f3460,color:#fff
```

### Receiver Use Cases
```mermaid
flowchart LR
    %% Actors
    Receiver((Email Receiver))
    IMAP[[Gmail / IMAP Server]]
    QKD[[Simulated QKD Network]]

    %% System Boundary
    subgraph QuMail System
        Fetch([Fetch Emails])
        ParseMIME([Extract Secure MIME])
        ReqDecKey([Request Decryption Key])
        Decrypt([Decrypt & Verify Envelope])
        View([View Plaintext Email])
    end

    %% Relationships
    IMAP --> Fetch
    Receiver --> View
    
    Fetch -.->|"triggers"| ParseMIME
    ParseMIME -.->|"outputs"| Decrypt
    
    Decrypt -.->|"requires"| ReqDecKey
    ReqDecKey --> QKD
    
    Decrypt -.->|"provides"| View
    
    %% Styling
    style IMAP fill:#2d2d44,stroke:#ff6b6b,color:#fff
    style QKD fill:#1a1a2e,stroke:#0f3460,color:#fff
```

---

## 2. Updated Security Data Flow Diagrams

Here are the detailed data flow diagrams with precise Sender and Receiver flows for all three security levels.

### Level 1: Quantum Secure OTP

#### L1 Sender (Encryption) Flow
```mermaid
flowchart TD
    %% Components
    PT["Plaintext Email"]
    KM["Key Manager (Port 8100)"]
    API["QuMail Backend API"]
    XOR{"XOR Engine"}
    MIME["MIME Builder"]
    SMTP["SMTP Server"]
    
    %% Data Flow
    PT -->|"Raw Text String"| API
    API -->|"Request OTP bytes"| KM
    KM -->|"Returns: raw_bytes + key_id"| API
    
    API -->|"1: plaintext_bytes"| XOR
    API -->|"2: raw_bytes"| XOR
    
    XOR -->|"Ciphertext_bytes"| MIME
    API -->|"key_id & L1 headers"| MIME
    
    MIME -->|"Base64 JSON Envelope"| SMTP
    
    %% Styling
    style XOR fill:#e94560,color:#fff
    style KM fill:#0f3460,color:#fff
```

#### L1 Receiver (Decryption) Flow
```mermaid
flowchart TD
    %% Components
    IMAP["IMAP Server"]
    MIME["MIME Parser"]
    API["QuMail Backend API"]
    KM["Key Manager (Port 8100)"]
    XOR{"XOR Engine"}
    UI["QuMail Frontend UI"]
    
    %% Data Flow
    IMAP -->|"Base64 JSON Envelope"| MIME
    MIME -->|"Extracts: key_id"| API
    MIME -->|"Extracts: Ciphertext_bytes"| XOR
    
    API -->|"Request exact key_id"| KM
    KM -->|"Returns: matching raw_bytes"| API
    API -->|"raw_bytes"| XOR
    
    XOR -->|"Decoded plaintext_bytes"| UI
    
    %% Styling
    style XOR fill:#e94560,color:#fff
    style KM fill:#0f3460,color:#fff
```

---

### Level 2: Quantum-Aided AES

#### L2 Sender (Encryption) Flow
```mermaid
flowchart TD
    %% Components
    PT["Plaintext Email"]
    KM["Key Manager"]
    HKDF{"HKDF Function"}
    RNG{"OS Randomizer"}
    AES{"AES-256-GCM Engine"}
    MIME["MIME Builder"]
    SMTP["SMTP Server"]
    
    %% Data Flow
    PT -->|"Raw Text String"| AES
    
    KM -->|"32-byte QKD Seed + key_id"| HKDF
    HKDF -->|"Derives clean 256-bit Key"| AES
    
    RNG -->|"Generates 12-byte Nonce"| AES
    
    AES -->|"Ciphertext"| MIME
    AES -->|"16-byte Auth Tag"| MIME
    RNG -->|"Nonce"| MIME
    KM -->|"key_id"| MIME
    
    MIME -->|"Packages Envelope"| SMTP
    
    %% Styling
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```

#### L2 Receiver (Decryption) Flow
```mermaid
flowchart TD
    %% Components
    IMAP["IMAP Server"]
    MIME["MIME Parser"]
    KM["Key Manager"]
    HKDF{"HKDF Function"}
    AES{"AES-256-GCM Engine"}
    UI["QuMail Frontend UI"]
    ERR["Auth Error Handler"]
    
    %% Data Flow
    IMAP -->|"Base64 Envelope"| MIME
    
    MIME -->|"Extracts: key_id"| KM
    KM -->|"Returns: exact 32-byte QKD Seed"| HKDF
    HKDF -->|"Rebuilds 256-bit Key"| AES
    
    MIME -->|"Ciphertext"| AES
    MIME -->|"Nonce"| AES
    MIME -->|"Auth Tag"| AES
    
    AES -->|"Tag Verifies -> Plaintext"| UI
    AES -->|"Tag Fails -> Abort"| ERR
    
    %% Styling
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```

---

### Level 3: Post-Quantum Crypto (Hybrid)

#### L3 Sender (Encryption) Flow
```mermaid
flowchart TD
    %% Components
    PT["Plaintext Email"]
    PUB["Alice's Kyber Public Key"]
    KYB{"Kyber.Encapsulate"}
    KM["Key Manager"]
    HKDF{"Hybrid HKDF"}
    AES{"AES-256-GCM Engine"}
    MIME["MIME Builder"]
    SMTP["SMTP Server"]
    
    %% Data Flow
    PUB -->|"Input to Kyber"| KYB
    KYB -->|"Generates Shared Secret"| HKDF
    KYB -->|"Kyber Ciphertext"| MIME
    
    KM -->|"32-byte QKD Seed + key_id"| HKDF
    
    HKDF -->|"Mixes Secret + Seed -> Ultimate Key"| AES
    
    PT -->|"Raw Text String"| AES
    AES -->|"AES Ciphertext + Nonce + Tag"| MIME
    
    KM -->|"qkd_key_id"| MIME
    
    MIME -->|"Double-layered Envelope"| SMTP
    
    %% Styling
    style KYB fill:#4b1d52,color:#fff
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```

#### L3 Receiver (Decryption) Flow
```mermaid
flowchart TD
    %% Components
    IMAP["IMAP Server"]
    MIME["MIME Parser"]
    PRIV["Alice's Kyber Private Key"]
    KYB{"Kyber.Decapsulate"}
    KM["Key Manager"]
    HKDF{"Hybrid HKDF"}
    AES{"AES-256-GCM Engine"}
    UI["QuMail Frontend UI"]
    
    %% Data Flow
    IMAP -->|"Base64 Envelope"| MIME
    
    MIME -->|"Extracts Kyber Ciphertext"| KYB
    PRIV -->|"Input to solve puzzle"| KYB
    KYB -->|"Recovers exact Shared Secret"| HKDF
    
    MIME -->|"Extracts qkd_key_id"| KM
    KM -->|"Returns exact 32-byte QKD Seed"| HKDF
    
    HKDF -->|"Mixes Secret + Seed -> Ultimate Key"| AES
    
    MIME -->|"AES Ciphertext + Nonce + Tag"| AES
    
    AES -->|"Tag Verifies -> Plaintext"| UI
    
    %% Styling
    style KYB fill:#4b1d52,color:#fff
    style AES fill:#e94560,color:#fff
    style HKDF fill:#1a1a2e,color:#fff
    style KM fill:#0f3460,color:#fff
```
