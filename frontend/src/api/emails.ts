import { api } from './client'
import type { Email } from '../types/email'
import type { SendEmailRequest, SendEmailResponse } from '../types/api'

// Extended interface to handle the file objects in the component
export interface SendEmailForm extends Omit<SendEmailRequest, 'attachments'> {
    attachments: File[]
}

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

export async function getEmail(messageId: string, folder: string = 'INBOX'): Promise<Email> {
    return api.get<Email>(`/emails/${messageId}?folder=${folder}`)
}

export async function sendEmail(request: SendEmailForm): Promise<SendEmailResponse> {
    const formData = new FormData()

    // Append array fields
    // Backend expects 'to', 'cc' as repeated fields or comma-separated strings.
    // Standard FormData append repeats the key for arrays.
    request.to.forEach(email => formData.append('to', email))
    if (request.cc) request.cc.forEach(email => formData.append('cc', email))

    formData.append('subject', request.subject)
    formData.append('body', request.body)
    formData.append('security_level', request.security_level.toString())

    // Append files
    if (request.attachments && request.attachments.length > 0) {
        request.attachments.forEach(file => {
            formData.append('attachments', file)
        })
    }

    return api.post<SendEmailResponse>('/emails/send', formData)
}

export async function deleteEmail(messageId: string): Promise<{ success: boolean }> {
    return api.delete<{ success: boolean }>(`/emails/${messageId}`)
}

export async function saveDraft(request: SendEmailRequest): Promise<{ draft_id: string }> {
    return api.post<{ draft_id: string }>('/emails/draft', request)
}

export async function downloadAttachment(
    messageId: string,
    attachmentId: string,
    filename: string
): Promise<void> {
    const token = (await import('./client')).getAuthToken()
    const response = await fetch(`/api/v1/emails/${messageId}/attachment/${attachmentId}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    })

    if (!response.ok) {
        throw new Error('Failed to download attachment')
    }

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
}
