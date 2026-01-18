import { api } from './client'

export interface Settings {
    theme: 'light' | 'dark'
    security_level: number
}

export async function getSettings(): Promise<Settings> {
    return api.get<Settings>('/settings')
}

export async function updateSettings(settings: Settings): Promise<Settings> {
    return api.post<Settings>('/settings', settings)
}
