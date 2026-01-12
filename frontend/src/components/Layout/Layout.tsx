import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { Inbox, Send, FileEdit, Shield, Settings, PenSquare } from 'lucide-react'
import Sidebar from './Sidebar'
import Header from './Header'
import './Layout.css'

export default function Layout() {
    return (
        <div className="layout">
            <Sidebar />
            <div className="layout-main">
                <Header />
                <main className="layout-content">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
