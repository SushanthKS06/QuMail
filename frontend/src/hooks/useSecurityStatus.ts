import { useState, useEffect, useCallback } from 'react'
import { getSecurityStatus } from '../api/security'
import type { SecurityStatus } from '../types/api'

export function useSecurityStatus() {
    const [status, setStatus] = useState<SecurityStatus | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const refresh = useCallback(async () => {
        setIsLoading(true)
        setError(null)

        try {
            const data = await getSecurityStatus()
            setStatus(data)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to get security status')
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        refresh()

        // Refresh every 30 seconds
        const interval = setInterval(refresh, 30000)
        return () => clearInterval(interval)
    }, [refresh])

    return {
        status,
        isLoading,
        error,
        refresh,
    }
}
