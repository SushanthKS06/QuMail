import { useState, useEffect } from 'react'
import ChatList from './ChatList'
import ChatWindow from './ChatWindow'
import { getSessions, createSession } from '../../api/chat'
import type { ChatSession } from '../../types/chat'
import { useToast } from '../Toast/Toast'
import './ChatLayout.css'

export default function ChatLayout() {
    const [sessions, setSessions] = useState<ChatSession[]>([])
    const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
    const { addToast } = useToast()

    useEffect(() => {
        loadSessions()
        // Poll for new sessions every 5 seconds
        const interval = setInterval(loadSessions, 5000)
        return () => clearInterval(interval)
    }, [])

    async function loadSessions() {
        try {
            const fetched = await getSessions()
            setSessions(fetched)
        } catch (error) {
            console.error('Failed to load sessions', error)
        }
    }

    async function handleNewChat() {
        const peerId = prompt('Enter recipient email address:')
        if (!peerId) return

        try {
            const newSession = await createSession({
                peer_id: peerId,
                security_level: 2 // Default to AES
            })
            setSessions(prev => [newSession, ...prev])
            setSelectedSessionId(newSession.id)
            addToast('Chat started', 'success')
        } catch (error) {
            addToast('Failed to start chat', 'error')
        }
    }

    return (
        <div className="chat-layout">
            <div className="chat-sidebar">
                <div className="chat-sidebar-header">
                    <h2>Chats</h2>
                    <button onClick={handleNewChat} className="new-chat-btn">+</button>
                </div>
                <ChatList
                    sessions={sessions}
                    selectedId={selectedSessionId}
                    onSelect={setSelectedSessionId}
                />
            </div>
            <div className="chat-main">
                {selectedSessionId ? (
                    <ChatWindow sessionId={selectedSessionId} />
                ) : (
                    <div className="chat-placeholder">
                        <p>Select a conversation to start chatting securely.</p>
                    </div>
                )}
            </div>
        </div>
    )
}
