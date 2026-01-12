const API_BASE = '/api/v1'

let authToken: string | null = null

export function setAuthToken(token: string) {
    authToken = token
}

export function getAuthToken(): string | null {
    return authToken
}

async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(authToken && { Authorization: `Bearer ${authToken}` }),
        ...options.headers,
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    })

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Request failed: ${response.status}`)
    }

    return response.json()
}

export const api = {
    get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
    post: <T>(endpoint: string, data?: unknown) =>
        request<T>(endpoint, {
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined,
        }),
    put: <T>(endpoint: string, data?: unknown) =>
        request<T>(endpoint, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined,
        }),
    delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
}
