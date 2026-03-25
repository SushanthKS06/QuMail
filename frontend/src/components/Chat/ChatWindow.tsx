import { useState, useEffect, useRef } from 'react'
import { Send, Lock } from 'lucide-react'
import { getMessages, sendMessage, getSession } from '../../api/chat'
import type { ChatMessage, ChatSession } from '../../types/chat'

import { useToast } from '../Toast/Toast'
import './ChatWindow.css'

interface Props {
    sessionId: string
}

export default function ChatWindow({ sessionId }: Props) {
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [session, setSession] = useState<ChatSession | null>(null)
    const [input, setInput] = useState('')
    const [securityLevel, setSecurityLevel] = useState<1 | 2 | 3 | 4>(2)
    const [sending, setSending] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const { addToast } = useToast()

    useEffect(() => {
        loadData()
        const interval = setInterval(() => loadMessages(), 3000)
        return () => clearInterval(interval)
    }, [sessionId])

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    async function loadData() {
        try {
            const [sess, msgs] = await Promise.all([
                getSession(sessionId),
                getMessages(sessionId)
            ])
            setSession(sess)
            setMessages(msgs)
        } catch (error) {
            console.error('Failed to load chat data', error)
        }
    }

    async function loadMessages() {
        try {
            const msgs = await getMessages(sessionId)
            // Simple replacement for now, could act smarter with diffs
            setMessages(msgs)
        } catch (error) {
            console.error('Failed to poll messages', error)
        }
    }

    async function handleSend() {
        if (!input.trim() || sending) return

        setSending(true)
        try {
            const newMsg = await sendMessage(sessionId, {
                content: input,
                security_level: securityLevel
            })
            setMessages(prev => [...prev, newMsg])
            setInput('')
        } catch (error) {
            addToast('Failed to send message', 'error')
        } finally {
            setSending(false)
        }
    }

    function scrollToBottom() {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    return (
        <div className="chat-window">
            <div className="chat-header">
                <div className="chat-header-info">
                    <h3>{session?.peer_id || 'Loading...'}</h3>
                    {session && (
                        <div className="chat-security-badge">
                            <Lock size={12} />
                            <span>Encrypted</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="chat-messages">
                {messages.map(msg => (
                    <div
                        key={msg.id}
                        className={`message-bubble ${msg.is_self ? 'self' : 'peer'}`}
                    >
                        <div className="message-content">
                            {msg.content}
                        </div>
                        <div className="message-meta">
                            <span className="security-dot level-2" title={`Level ${msg.security_level}`}></span>
                            <span className="time">
                                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area">
                <div className="chat-toolbar">
                    <span className="security-label">Security:</span>
                    <div className="mini-selector">
                        <select
                            value={securityLevel}
                            onChange={(e) => setSecurityLevel(Number(e.target.value) as any)}
                        >
                            <option value="1">OTP (L1)</option>
                            <option value="2">AES (L2)</option>
                            <option value="3">PQC (L3)</option>
                        </select>
                    </div>
                </div>
                <div className="input-row">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Type a secure message..."
                        disabled={sending}
                    />
                    <button onClick={handleSend} disabled={sending || !input.trim()}>
                        <Send size={18} />
                    </button>
                </div>
            </div>
        </div>
    )
}
