import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2, Reply, Forward, Download } from 'lucide-react'
import { getEmail, deleteEmail } from '../../api/emails'
import SecurityBadge from '../Security/SecurityBadge'
import type { Email } from '../../types/email'
import './EmailView.css'

export default function EmailView() {
    const { messageId } = useParams<{ messageId: string }>()
    const navigate = useNavigate()
    const [email, setEmail] = useState<Email | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (messageId) {
            loadEmail(messageId)
        }
    }, [messageId])

    async function loadEmail(id: string) {
        setIsLoading(true)
        setError(null)

        try {
            const data = await getEmail(id)
            setEmail(data)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load email')
        } finally {
            setIsLoading(false)
        }
    }

    async function handleDelete() {
        if (!messageId || !confirm('Delete this email?')) return

        try {
            await deleteEmail(messageId)
            navigate('/inbox')
        } catch (err) {
            alert('Failed to delete email')
        }
    }

    if (isLoading) {
        return (
            <div className="email-view-loading">
                <div className="loading-spinner"></div>
                <p>Loading email...</p>
            </div>
        )
    }

    if (error || !email) {
        return (
            <div className="email-view-error">
                <p>{error || 'Email not found'}</p>
                <button onClick={() => navigate('/inbox')}>Back to Inbox</button>
            </div>
        )
    }

    return (
        <div className="email-view">
            <div className="email-view-toolbar">
                <button className="toolbar-button" onClick={() => navigate(-1)}>
                    <ArrowLeft size={18} />
                    <span>Back</span>
                </button>

                <div className="toolbar-actions">
                    <button className="toolbar-button">
                        <Reply size={18} />
                        <span>Reply</span>
                    </button>
                    <button className="toolbar-button">
                        <Forward size={18} />
                        <span>Forward</span>
                    </button>
                    <button className="toolbar-button danger" onClick={handleDelete}>
                        <Trash2 size={18} />
                        <span>Delete</span>
                    </button>
                </div>
            </div>

            <div className="email-view-content">
                <div className="email-view-header">
                    <div className="email-view-title">
                        <h1>{email.subject}</h1>
                        <SecurityBadge level={email.security_level} size="large" showLabel />
                    </div>

                    <div className="email-meta">
                        <div className="email-meta-row">
                            <span className="meta-label">From:</span>
                            <span className="meta-value">{email.from}</span>
                        </div>
                        <div className="email-meta-row">
                            <span className="meta-label">To:</span>
                            <span className="meta-value">{email.to.join(', ')}</span>
                        </div>
                        {email.cc && email.cc.length > 0 && (
                            <div className="email-meta-row">
                                <span className="meta-label">Cc:</span>
                                <span className="meta-value">{email.cc.join(', ')}</span>
                            </div>
                        )}
                        <div className="email-meta-row">
                            <span className="meta-label">Date:</span>
                            <span className="meta-value">
                                {new Date(email.received_at).toLocaleString()}
                            </span>
                        </div>
                        {email.key_id && (
                            <div className="email-meta-row">
                                <span className="meta-label">Key ID:</span>
                                <span className="meta-value key-id">{email.key_id}</span>
                            </div>
                        )}
                    </div>
                </div>

                <div className="email-body">
                    {email.html_body ? (
                        <div dangerouslySetInnerHTML={{ __html: email.html_body }} />
                    ) : (
                        <pre>{email.body}</pre>
                    )}
                </div>

                {email.attachments && email.attachments.length > 0 && (
                    <div className="email-attachments">
                        <h3>Attachments ({email.attachments.length})</h3>
                        <div className="attachment-list">
                            {email.attachments.map((att) => (
                                <div key={att.id} className="attachment-item">
                                    <span className="attachment-name">{att.filename}</span>
                                    <span className="attachment-size">{formatSize(att.size)}</span>
                                    <button className="attachment-download">
                                        <Download size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

function formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
