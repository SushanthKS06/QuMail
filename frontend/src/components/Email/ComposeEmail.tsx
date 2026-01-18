import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, X, Paperclip } from 'lucide-react'
import { sendEmail } from '../../api/emails'
import SecurityLevelSelector from '../Security/SecurityLevelSelector'
import type { SecurityLevel } from '../../types/email'
import { useToast } from '../Toast/Toast'
import './ComposeEmail.css'

export default function ComposeEmail() {
    const navigate = useNavigate()
    const { addToast } = useToast()
    const [attachments, setAttachments] = useState<File[]>([])
    const [to, setTo] = useState('')
    const [cc, setCc] = useState('')
    const [subject, setSubject] = useState('')
    const [body, setBody] = useState('')
    const [securityLevel, setSecurityLevel] = useState<SecurityLevel>(2)
    const [isSending, setIsSending] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setAttachments(prev => [...prev, ...Array.from(e.target.files!)])
        }
    }

    const removeAttachment = (index: number) => {
        setAttachments(prev => prev.filter((_, i) => i !== index))
    }

    async function handleSend() {
        if (!to.trim()) {
            setError('Please enter at least one recipient')
            return
        }
        if (!subject.trim()) {
            setError('Please enter a subject')
            return
        }
        if (!body.trim() && attachments.length === 0) {
            setError('Please enter a message or add attachments')
            return
        }

        setIsSending(true)
        setError(null)

        try {
            const toAddresses = to.split(',').map(e => e.trim()).filter(Boolean)
            const ccAddresses = cc ? cc.split(',').map(e => e.trim()).filter(Boolean) : []

            const result = await sendEmail({
                to: toAddresses,
                cc: ccAddresses,
                subject,
                body,
                security_level: securityLevel,
                attachments: attachments as any,
            })

            if (result.success) {
                addToast('Email sent successfully', 'success')
                navigate('/sent')
            } else {
                const errorMessage = result.error || 'Failed to send email'
                setError(errorMessage)
                addToast(errorMessage, 'error')
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to send email'
            setError(errorMessage)
            addToast(errorMessage, 'error')
        } finally {
            setIsSending(false)
        }
    }

    function handleDiscard() {
        if (body.trim() || subject.trim() || attachments.length > 0) {
            if (!confirm('Discard this email?')) return
        }
        navigate(-1)
    }

    return (
        <div className="compose">
            <div className="compose-header">
                <h2>New Message</h2>
                <div className="compose-actions">
                    <button
                        className="compose-button discard"
                        onClick={handleDiscard}
                    >
                        <X size={18} />
                        <span>Discard</span>
                    </button>
                    <button
                        className="compose-button send"
                        onClick={handleSend}
                        disabled={isSending}
                    >
                        <Send size={18} />
                        <span>{isSending ? 'Sending...' : 'Send'}</span>
                    </button>
                </div>
            </div>

            {error && (
                <div className="compose-error">
                    {error}
                </div>
            )}

            <div className="compose-form">
                <div className="form-row">
                    <label>To:</label>
                    <input
                        type="text"
                        value={to}
                        onChange={(e) => setTo(e.target.value)}
                        placeholder="recipient@example.com"
                    />
                </div>

                <div className="form-row">
                    <label>Cc:</label>
                    <input
                        type="text"
                        value={cc}
                        onChange={(e) => setCc(e.target.value)}
                        placeholder="cc@example.com (optional)"
                    />
                </div>

                <div className="form-row">
                    <label>Subject:</label>
                    <input
                        type="text"
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        placeholder="Email subject"
                    />
                </div>

                <div className="form-row security-row">
                    <label>Security:</label>
                    <SecurityLevelSelector
                        value={securityLevel}
                        onChange={setSecurityLevel}
                    />
                </div>

                <div className="form-row body-row">
                    <textarea
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                        placeholder="Write your message..."
                        rows={15}
                    />
                </div>

                {attachments.length > 0 && (
                    <div className="attachments-list">
                        {attachments.map((file, i) => (
                            <div key={i} className="attachment-chip">
                                <span className="attachment-name">{file.name}</span>
                                <span className="attachment-size">({(file.size / 1024).toFixed(1)} KB)</span>
                                <button onClick={() => removeAttachment(i)} className="remove-attachment">
                                    <X size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                <div className="form-row attachments-row">
                    <label className="attach-button">
                        <Paperclip size={16} />
                        <span>Attach files</span>
                        <input
                            type="file"
                            multiple
                            onChange={handleFileSelect}
                            style={{ display: 'none' }}
                        />
                    </label>
                </div>
            </div>
        </div>
    )
}
