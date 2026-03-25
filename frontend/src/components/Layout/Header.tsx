import { useLocation } from 'react-router-dom'
import { RefreshCw, Settings, LogOut } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import './Header.css'

interface HeaderProps {
    onSettingsClick?: () => void
    onRefresh?: () => void
}

export default function Header({ onSettingsClick, onRefresh }: HeaderProps) {
    const location = useLocation()
    const { accounts } = useAuth()

    const getTitle = () => {
        const path = location.pathname
        if (path.startsWith('/inbox')) return 'Inbox'
        if (path.startsWith('/sent')) return 'Sent'
        if (path.startsWith('/drafts')) return 'Drafts'
        if (path.startsWith('/compose')) return 'Compose'
        if (path.startsWith('/email')) return 'Email'
        return 'QuMail'
    }

    const handleRefresh = () => {
        if (onRefresh) {
            onRefresh()
        } else {
            window.location.reload()
        }
    }

    const handleLogout = () => {
        localStorage.removeItem('qumail_token')
        localStorage.setItem('qumail_logged_out', 'true')
        window.location.reload()
    }

    return (
        <header className="header">
            <h1 className="header-title">{getTitle()}</h1>

            <div className="header-actions">
                <button className="header-button" title="Refresh" onClick={handleRefresh}>
                    <RefreshCw size={18} />
                </button>
                <button className="header-button" title="Settings" onClick={onSettingsClick}>
                    <Settings size={18} />
                </button>

                <div className="header-user">
                    <span className="user-email">{accounts[0]?.email || 'Not connected'}</span>
                    <button className="header-button" onClick={handleLogout} title="Logout">
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </header>
    )
}
