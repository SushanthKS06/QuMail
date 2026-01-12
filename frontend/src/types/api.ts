export interface ApiResponse<T> {
    data?: T
    error?: string
    success: boolean
}

export interface AuthStatus {
    authenticated: boolean
    accounts: {
        email: string
        provider: string
        connected_at: string
    }[]
}

export interface SecurityStatus {
    km_connected: boolean
    km_url: string
    available_key_material: {
        otp_bytes: number
        aes_keys: number
        pqc_keys: number
    }
    last_key_sync?: string
    supported_levels: number[]
}

export interface SendEmailRequest {
    to: string[]
    cc?: string[]
    subject: string
    body: string
    security_level: number
}

export interface SendEmailResponse {
    success: boolean
    message_id?: string
    key_id?: string
    security_level_used: number
    error?: string
}
