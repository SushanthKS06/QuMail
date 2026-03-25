import { api } from './client'
import type { SecurityStatus } from '../types/api'

export async function getSecurityStatus(): Promise<SecurityStatus> {
    return api.get<SecurityStatus>('/security/status')
}

export async function checkRecipientCapability(email: string): Promise<{
    email: string
    is_qumail_user: boolean
    supported_levels: number[]
}> {
    return api.get(`/security/capabilities/${encodeURIComponent(email)}`)
}

export async function refreshKeys(keyType: string, size: number): Promise<{
    success: boolean
    keys_added: number
}> {
    return api.post('/security/refresh-keys', { key_type: keyType, size })
}

export async function getSecurityLevels(): Promise<{
    levels: {
        level: number
        name: string
        description: string
        requirements: string
        quantum_safe: boolean
        recommended_for: string
    }[]
    default_level: number
}> {
    return api.get('/security/levels')
}

export interface TestResult {
    test_name: string
    security_level: number
    success: boolean
    duration_ms: number
    message: string
    details?: Record<string, number>
}

export interface DiagnosticsResult {
    overall_success: boolean
    tests: TestResult[]
    run_at: string
    total_duration_ms: number
}

export async function runDiagnostics(): Promise<DiagnosticsResult> {
    return api.post<DiagnosticsResult>('/diagnostics/run')
}
