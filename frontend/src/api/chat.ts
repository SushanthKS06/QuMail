import { api } from './client'
import type { ChatSession, ChatMessage, CreateSessionRequest, SendMessageRequest } from '../types/chat'

export async function getSessions(): Promise<ChatSession[]> {
    return api.get<ChatSession[]>('/chat/sessions')
}

export async function createSession(request: CreateSessionRequest): Promise<ChatSession> {
    return api.post<ChatSession>('/chat/sessions', request)
}

export async function getSession(id: string): Promise<ChatSession> {
    return api.get<ChatSession>(`/chat/sessions/${id}`)
}

export async function getMessages(sessionId: string): Promise<ChatMessage[]> {
    return api.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`)
}

export async function sendMessage(sessionId: string, request: SendMessageRequest): Promise<ChatMessage> {
    return api.post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, request)
}
