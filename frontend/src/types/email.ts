export interface Email {
    message_id: string
    from: string
    to: string[]
    cc?: string[]
    subject: string
    body?: string
    preview?: string
    html_body?: string
    received_at: string
    security_level: SecurityLevel
    key_id?: string
    has_attachments: boolean
    is_read: boolean
    attachments?: Attachment[]
}

export interface Attachment {
    id: string
    filename: string
    size: number
    content_type: string
}

export type SecurityLevel = 1 | 2 | 3 | 4

export interface SecurityLevelInfo {
    level: SecurityLevel
    name: string
    description: string
    icon: string
    color: string
    quantum_safe: boolean
}

export const SECURITY_LEVELS: Record<SecurityLevel, SecurityLevelInfo> = {
    1: {
        level: 1,
        name: 'Quantum Secure OTP',
        description: 'One-Time Pad with QKD keys - Information-theoretic security',
        icon: '🔐',
        color: 'var(--color-security-1)',
        quantum_safe: true,
    },
    2: {
        level: 2,
        name: 'Quantum-Aided AES',
        description: 'AES-256-GCM with QKD-derived keys',
        icon: '🛡️',
        color: 'var(--color-security-2)',
        quantum_safe: false,
    },
    3: {
        level: 3,
        name: 'Post-Quantum Crypto',
        description: 'Kyber + Dilithium hybrid encryption',
        icon: '⚛️',
        color: 'var(--color-security-3)',
        quantum_safe: true,
    },
    4: {
        level: 4,
        name: 'No Security',
        description: 'Plain text email - No encryption',
        icon: '📧',
        color: 'var(--color-security-4)',
        quantum_safe: false,
    },
}
