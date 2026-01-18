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
    if (request.attachments && request.attachments.length > 0) {
        const formData = new FormData()
        // Append all text fields
        request.to.forEach(email => formData.append('to', email))
        if (request.cc) request.cc.forEach(email => formData.append('cc', email))
        formData.append('subject', request.subject)
        formData.append('body', request.body)
        formData.append('security_level', request.security_level.toString())

        // Append files
        // Note: attachments in request logic might be File objects, but the interface definition 
        // needs to be compatible. If 'attachments' in SendEmailRequest is string[], we need to fix the type too.
        // Assuming we pass 'File[]' from the component, we might need a separate interface or override.
        // Let's cast to any for the implementation or update the type definition.

        // We will assume the component passes { ...request, attachments: File[] } 
        // effectively ignoring the strict type for a moment or we update the type.

        const files = request.attachments as unknown as File[]
        files.forEach(file => {
            formData.append('attachments', file)
        })

        return api.post<SendEmailResponse>('/emails/send', formData)
    }

    // Fallback for no attachments (old behavior, but backend now expects Form or similar)
    // Actually backend `emails_endpoint` now expects Form data for fields even without attachments.
    // So we should ALWAYS use FormData or x-www-form-urlencoded if we want to be consistent 
    // with the backend change I made (Form(...) parameters).
    // Let's switch to FormData for all requests to this endpoint.

    const formData = new FormData()
    request.to.forEach(email => formData.append('to', email))
    if (request.cc) request.cc.forEach(email => formData.append('cc', email))
    formData.append('subject', request.subject)
    formData.append('body', request.body)
    formData.append('security_level', request.security_level.toString())

    return api.post<SendEmailResponse>('/emails/send', formData)
}

export async function deleteEmail(messageId: string): Promise<{ success: boolean }> {
    return api.delete<{ success: boolean }>(`/emails/${messageId}`)
}

export async function saveDraft(request: SendEmailRequest): Promise<{ draft_id: string }> {
    return api.post<{ draft_id: string }>('/emails/draft', request)
}
