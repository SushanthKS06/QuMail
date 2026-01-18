import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import SettingsModal from '../Settings/SettingsModal'
import './Layout.css'

export default function Layout() {
    const [isSettingsOpen, setIsSettingsOpen] = useState(false)

    return (
        <div className="layout">
            <Sidebar />
            <div className="layout-main">
                <Header onSettingsClick={() => setIsSettingsOpen(true)} />
                <main className="layout-content">
                    <Outlet />
                </main>
            </div>
            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        </div>
    )
}
