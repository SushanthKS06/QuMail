import { useState, useCallback } from 'react'
import { getAuthStatus, generateToken } from '../api/auth'
import { setAuthToken } from '../api/client'

interface AuthState {
    isAuthenticated: boolean
    isLoading: boolean
    accounts: { email: string; provider: string }[]
    error: string | null
}

const API_SECRET = import.meta.env.VITE_API_SECRET || 'change_this_to_another_random_string'

export function useAuth() {
    const [state, setState] = useState<AuthState>({
        isAuthenticated: false,
        isLoading: true,
        accounts: [],
        error: null,
    })

    const checkAuth = useCallback(async () => {
        try {
            let token = localStorage.getItem('qumail_token')

            if (!token) {
                try {
                    const tokenResponse = await generateToken(API_SECRET)
                    token = tokenResponse.access_token
                    localStorage.setItem('qumail_token', token)
                } catch (tokenError) {
                    console.error('Failed to get API token:', tokenError)
                    setState({
                        isAuthenticated: false,
                        isLoading: false,
                        accounts: [],
                        error: 'Failed to authenticate with backend',
                    })
                    return
                }
            }

            setAuthToken(token)

            const status = await getAuthStatus()

            setState({
                isAuthenticated: status.authenticated,
                isLoading: false,
                accounts: status.accounts,
                error: null,
            })
        } catch (error) {
            console.error('Auth check failed:', error)
            localStorage.removeItem('qumail_token')
            setState({
                isAuthenticated: false,
                isLoading: false,
                accounts: [],
                error: error instanceof Error ? error.message : 'Authentication failed',
            })
        }
    }, [])

    const login = useCallback(async (provider: 'gmail' | 'yahoo' = 'gmail') => {
        try {
            const endpoint = provider === 'yahoo'
                ? '/api/v1/auth/oauth/yahoo/init'
                : '/api/v1/auth/oauth/gmail/init'

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            })

            if (response.ok) {
                const data = await response.json()
                window.location.href = data.auth_url
            } else {
                console.error('OAuth init failed:', await response.text())
            }
        } catch (error) {
            console.error('Login failed:', error)
        }
    }, [])

    const logout = useCallback(() => {
        localStorage.removeItem('qumail_token')
        setState({
            isAuthenticated: false,
            isLoading: false,
            accounts: [],
            error: null,
        })
    }, [])

    return {
        ...state,
        checkAuth,
        login,
        logout,
    }
}
