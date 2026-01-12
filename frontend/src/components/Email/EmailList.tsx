import { useNavigate } from 'react-router-dom'
import { useEmails } from '../../hooks/useEmails'
import SecurityBadge from '../Security/SecurityBadge'
import { Mail, Paperclip } from 'lucide-react'
import './EmailList.css'

interface Props {
    folder: string
}

export default function EmailList({ folder }: Props) {
    const navigate = useNavigate()
    const { emails, total, isLoading, error, hasMore, loadMore, refresh } = useEmails(folder)

    if (isLoading && emails.length === 0) {
        return (
            <div className="email-list-loading">
                <div className="loading-spinner"></div>
                <p>Loading emails...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="email-list-error">
                <p>{error}</p>
                <button onClick={refresh}>Retry</button>
            </div>
        )
    }

    if (emails.length === 0) {
        return (
            <div className="email-list-empty">
                <Mail size={48} strokeWidth={1} />
                <h3>No emails</h3>
                <p>This folder is empty</p>
            </div>
        )
    }

    return (
        <div className="email-list">
            <div className="email-list-header">
                <span className="email-count">{total} emails</span>
            </div>

            <div className="email-items">
                {emails.map((email) => (
                    <div
                        key={email.message_id}
                        className={`email-item ${!email.is_read ? 'unread' : ''}`}
                        onClick={() => navigate(`/email/${email.message_id}`)}
                    >
                        <div className="email-item-left">
                            <SecurityBadge level={email.security_level} size="small" />
                        </div>

                        <div className="email-item-content">
                            <div className="email-item-header">
                                <span className="email-from">{email.from}</span>
                                <span className="email-date">
                                    {formatDate(email.received_at)}
                                </span>
                            </div>
                            <div className="email-subject">{email.subject}</div>
                            <div className="email-preview">{email.preview}</div>
                        </div>

                        <div className="email-item-right">
                            {email.has_attachments && (
                                <Paperclip size={14} className="attachment-icon" />
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {hasMore && (
                <div className="email-list-footer">
                    <button
                        className="load-more-button"
                        onClick={loadMore}
                        disabled={isLoading}
                    >
                        {isLoading ? 'Loading...' : 'Load More'}
                    </button>
                </div>
            )}
        </div>
    )
}

function formatDate(dateStr: string): string {
    const date = new Date(dateStr)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (diffDays === 1) {
        return 'Yesterday'
    } else if (diffDays < 7) {
        return date.toLocaleDateString([], { weekday: 'short' })
    } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
}
