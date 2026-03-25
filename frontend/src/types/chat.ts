export interface ChatSession {
    id: string
    peer_id: string
    security_level: 1 | 2 | 3 | 4
    created_at: string
    is_active: boolean
}

export interface ChatMessage {
    id: string
    sender: string
    recipient: string
    content: string
    timestamp: string
    security_level: 1 | 2 | 3 | 4
    is_self: boolean
}

export interface CreateSessionRequest {
    peer_id: string
    security_level: number
}

export interface SendMessageRequest {
    content: string
    security_level: number
}
