import { useState, useCallback } from 'react'
import { getAuthStatus } from '../api/auth'
import { setAuthToken } from '../api/client'

interface AuthState {
    isAuthenticated: boolean
    isLoading: boolean
    accounts: { email: string; provider: string }[]
}

export function useAuth() {
    const [state, setState] = useState<AuthState>({
        isAuthenticated: false,
        isLoading: true,
        accounts: [],
    })

    const checkAuth = useCallback(async () => {
        try {
            const demoToken = localStorage.getItem('qumail_token') || 'demo-token'
            setAuthToken(demoToken)

            const status = await getAuthStatus()

            setState({
                isAuthenticated: status.authenticated,
                isLoading: false,
                accounts: status.accounts,
            })
        } catch (error) {
            console.error('Auth check failed:', error)
            setState({
                isAuthenticated: false,
                isLoading: false,
                accounts: [],
            })
        }
    }, [])

    const login = useCallback(async () => {
        try {
            const response = await fetch('/api/v1/auth/oauth/gmail/init', {
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
        })
    }, [])

    return {
        ...state,
        checkAuth,
        login,
        logout,
    }
}
