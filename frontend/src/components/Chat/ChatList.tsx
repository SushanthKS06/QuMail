import { ChatSession } from '../../types/chat'
import { MessageSquare } from 'lucide-react'
import './ChatList.css'

interface Props {
    sessions: ChatSession[]
    selectedId: string | null
    onSelect: (id: string) => void
}

export default function ChatList({ sessions, selectedId, onSelect }: Props) {
    if (sessions.length === 0) {
        return (
            <div className="chat-list-empty">
                <p>No active chats</p>
                <small>Click + to start</small>
            </div>
        )
    }

    return (
        <div className="chat-list">
            {sessions.map(session => (
                <div
                    key={session.id}
                    className={`chat-item ${session.id === selectedId ? 'selected' : ''}`}
                    onClick={() => onSelect(session.id)}
                >
                    <div className="chat-item-icon">
                        <MessageSquare size={20} />
                    </div>
                    <div className="chat-item-info">
                        <span className="peer-id">{session.peer_id}</span>
                        <span className="chat-date">
                            {new Date(session.created_at).toLocaleDateString()}
                        </span>
                    </div>
                </div>
            ))}
        </div>
    )
}
