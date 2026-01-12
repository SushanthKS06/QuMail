import { NavLink, useNavigate } from 'react-router-dom'
import { Inbox, Send, FileEdit, PenSquare, Shield } from 'lucide-react'
import { useSecurityStatus } from '../../hooks/useSecurityStatus'
import './Sidebar.css'

export default function Sidebar() {
    const navigate = useNavigate()
    const { status } = useSecurityStatus()

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="logo">
                    <Shield className="logo-icon" />
                    <span className="logo-text">QuMail</span>
                </div>
                <span className="logo-badge">Quantum Secure</span>
            </div>

            <button
                className="compose-button"
                onClick={() => navigate('/compose')}
            >
                <PenSquare size={18} />
                <span>Compose</span>
            </button>

            <nav className="sidebar-nav">
                <NavLink to="/inbox" className="nav-item">
                    <Inbox size={18} />
                    <span>Inbox</span>
                </NavLink>
                <NavLink to="/sent" className="nav-item">
                    <Send size={18} />
                    <span>Sent</span>
                </NavLink>
                <NavLink to="/drafts" className="nav-item">
                    <FileEdit size={18} />
                    <span>Drafts</span>
                </NavLink>
            </nav>

            <div className="sidebar-footer">
                <div className="security-status">
                    <div className="status-header">
                        <Shield size={16} />
                        <span>Key Manager</span>
                    </div>
                    <div className={`status-indicator ${status?.km_connected ? 'connected' : 'disconnected'}`}>
                        <span className="status-dot"></span>
                        <span>{status?.km_connected ? 'Connected' : 'Disconnected'}</span>
                    </div>
                    {status?.km_connected && (
                        <div className="key-stats">
                            <div className="stat">
                                <span className="stat-label">OTP</span>
                                <span className="stat-value">
                                    {formatBytes(status.available_key_material.otp_bytes)}
                                </span>
                            </div>
                            <div className="stat">
                                <span className="stat-label">AES Keys</span>
                                <span className="stat-value">{status.available_key_material.aes_keys}</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </aside>
    )
}

function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}
