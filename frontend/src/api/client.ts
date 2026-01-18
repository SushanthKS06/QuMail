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
    // Default to JSON, but allow override or removal (by passing undefined/null if needed, 
    // though HeadersInit is strict). 
    // Actually, simpler logic: check if body is FormData in options? No, options.body is Init.
    // Let's rely on the caller to handle the Content-Type header in options.headers
    // IF the caller passes a body that is FormData, they usually want to let browser set it.

    // We'll merge defaults. If options.headers provides Content-Type, it wins.
    // BUT we need a way to say "No Content-Type" (let browser set it).

    // Strategy:
    // 1. If options.body is FormData, DO NOT set application/json default.
    // 2. Else, set application/json default check if not already present.

    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData

    const defaults: HeadersInit = {}
    if (!isFormData) {
        defaults['Content-Type'] = 'application/json'
    }
    if (authToken) {
        defaults['Authorization'] = `Bearer ${authToken}`
    }

    const headers = new Headers(defaults)

    // Apply overrides
    if (options.headers) {
        new Headers(options.headers).forEach((value, key) => {
            headers.set(key, value)
        })
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    })

    if (!response.ok) {
        if (response.status === 401) {
            authToken = null
            window.dispatchEvent(new Event('qumail:unauthorized'))
        }
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Request failed: ${response.status}`)
    }

    return response.json()
}

// Helper to determine if we should stringify
function isFormData(data: unknown): data is FormData {
    return typeof FormData !== 'undefined' && data instanceof FormData
}

export const api = {
    get: <T>(endpoint: string, config?: RequestInit) => request<T>(endpoint, { ...config, method: 'GET' }),

    post: <T>(endpoint: string, data?: unknown, config?: RequestInit) => {
        const isForm = isFormData(data)
        return request<T>(endpoint, {
            ...config,
            method: 'POST',
            body: isForm ? (data as FormData) : (data ? JSON.stringify(data) : undefined),
            headers: {
                ...config?.headers,
                // Only set JSON content type if NOT FormData. 
                // Fetch automatically sets Content-Type with boundary for FormData.
                // If the user explicitly sets it in config, it overrides (but likely shouldn't for FormData).
                // However, our request() helper sets application/json by default. We need to handle that.
            }
        })
    },

    put: <T>(endpoint: string, data?: unknown, config?: RequestInit) => {
        const isForm = isFormData(data)
        return request<T>(endpoint, {
            ...config,
            method: 'PUT',
            body: isForm ? (data as FormData) : (data ? JSON.stringify(data) : undefined),
            headers: {
                ...config?.headers,
            }
        })
    },

    delete: <T>(endpoint: string, config?: RequestInit) => request<T>(endpoint, { ...config, method: 'DELETE' }),
}
