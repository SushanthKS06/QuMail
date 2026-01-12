import React from 'react'
import './ErrorBoundary.css'

interface ErrorState {
    hasError: boolean
    error: Error | null
    errorInfo: React.ErrorInfo | null
}

interface Props {
    children: React.ReactNode
    fallback?: React.ReactNode
}

/**
 * Error Boundary Component
 *
 * Catches JavaScript errors in child components and displays
 * a user-friendly error message instead of crashing the app.
 */
export class ErrorBoundary extends React.Component<Props, ErrorState> {
    constructor(props: Props) {
        super(props)
        this.state = { hasError: false, error: null, errorInfo: null }
    }

    static getDerivedStateFromError(error: Error): Partial<ErrorState> {
        return { hasError: true, error }
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('ErrorBoundary caught:', error, errorInfo)
        this.setState({ errorInfo })
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null })
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback
            }

            return (
                <div className="error-boundary">
                    <div className="error-content">
                        <div className="error-icon">⚠️</div>
                        <h2>Something went wrong</h2>
                        <p className="error-message">
                            {this.state.error?.message || 'An unexpected error occurred'}
                        </p>
                        <button className="retry-button" onClick={this.handleRetry}>
                            Try Again
                        </button>
                        {import.meta.env.DEV && (
                            <details className="error-details">
                                <summary>Error Details</summary>
                                <pre>{this.state.error?.stack}</pre>
                                <pre>{this.state.errorInfo?.componentStack}</pre>
                            </details>
                        )}
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}





