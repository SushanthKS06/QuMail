import { useLocation } from 'react-router-dom'
import { RefreshCw, Settings, LogOut } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import './Header.css'

export default function Header() {
    const location = useLocation()
    const { accounts, logout } = useAuth()

    const getTitle = () => {
        const path = location.pathname
        if (path.startsWith('/inbox')) return 'Inbox'
        if (path.startsWith('/sent')) return 'Sent'
        if (path.startsWith('/drafts')) return 'Drafts'
        if (path.startsWith('/compose')) return 'Compose'
        if (path.startsWith('/email')) return 'Email'
        return 'QuMail'
    }

    return (
        <header className="header">
            <h1 className="header-title">{getTitle()}</h1>

            <div className="header-actions">
                <button className="header-button" title="Refresh">
                    <RefreshCw size={18} />
                </button>
                <button className="header-button" title="Settings">
                    <Settings size={18} />
                </button>

                <div className="header-user">
                    <span className="user-email">{accounts[0]?.email || 'Not connected'}</span>
                    <button className="header-button" onClick={logout} title="Logout">
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </header>
    )
}
