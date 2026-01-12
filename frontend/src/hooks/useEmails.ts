import { useState, useEffect, useCallback } from 'react'
import { fetchEmails, type EmailListResponse } from '../api/emails'
import type { Email } from '../types/email'

interface EmailsState {
    emails: Email[]
    total: number
    hasMore: boolean
    isLoading: boolean
    error: string | null
}

export function useEmails(folder: string) {
    const [state, setState] = useState<EmailsState>({
        emails: [],
        total: 0,
        hasMore: false,
        isLoading: true,
        error: null,
    })
    const [page, setPage] = useState(1)

    const loadEmails = useCallback(async (pageNum: number = 1) => {
        setState(prev => ({ ...prev, isLoading: true, error: null }))

        try {
            const response = await fetchEmails(folder, pageNum)

            setState({
                emails: pageNum === 1 ? response.emails : [...state.emails, ...response.emails],
                total: response.total,
                hasMore: response.has_more,
                isLoading: false,
                error: null,
            })
        } catch (error) {
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: error instanceof Error ? error.message : 'Failed to load emails',
            }))
        }
    }, [folder])

    useEffect(() => {
        loadEmails(1)
        setPage(1)
    }, [folder])

    const loadMore = useCallback(() => {
        if (!state.isLoading && state.hasMore) {
            const nextPage = page + 1
            setPage(nextPage)
            loadEmails(nextPage)
        }
    }, [page, state.isLoading, state.hasMore, loadEmails])

    const refresh = useCallback(() => {
        setPage(1)
        loadEmails(1)
    }, [loadEmails])

    return {
        ...state,
        loadMore,
        refresh,
    }
}
