import { api } from './client'
import type { Email } from '../types/email'
import type { SendEmailRequest, SendEmailResponse } from '../types/api'

export interface EmailListResponse {
    emails: Email[]
    total: number
    has_more: boolean
}

export async function fetchEmails(
    folder: string,
    page: number = 1,
    limit: number = 20
): Promise<EmailListResponse> {
    return api.get<EmailListResponse>(
        `/emails?folder=${folder}&page=${page}&limit=${limit}`
    )
}

export async function getEmail(messageId: string): Promise<Email> {
    return api.get<Email>(`/emails/${messageId}`)
}

export async function sendEmail(request: SendEmailRequest): Promise<SendEmailResponse> {
    return api.post<SendEmailResponse>('/emails/send', request)
}

export async function deleteEmail(messageId: string): Promise<{ success: boolean }> {
    return api.delete<{ success: boolean }>(`/emails/${messageId}`)
}

export async function saveDraft(request: SendEmailRequest): Promise<{ draft_id: string }> {
    return api.post<{ draft_id: string }>('/emails/draft', request)
}
