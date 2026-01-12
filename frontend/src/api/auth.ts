import { api } from './client'
import type { AuthStatus } from '../types/api'

export async function getAuthStatus(): Promise<AuthStatus> {
    return api.get<AuthStatus>('/auth/status')
}

export async function initiateOAuth(): Promise<{ auth_url: string; state: string }> {
    return api.post('/auth/oauth/gmail/init')
}

export async function generateToken(appSecret: string): Promise<{ access_token: string; expires_in: number }> {
    return api.post('/auth/token', { app_secret: appSecret })
}
