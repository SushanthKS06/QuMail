import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ToastProvider } from './components/Toast/Toast'
import Layout from './components/Layout/Layout'
import EmailList from './components/Email/EmailList'
import EmailView from './components/Email/EmailView'
import ComposeEmail from './components/Email/ComposeEmail'
import LoginScreen from './components/Auth/LoginScreen'
import { useAuth } from './hooks/useAuth'

function App() {
    const { isAuthenticated, isLoading, checkAuth } = useAuth()

    useEffect(() => {
        checkAuth()

        // Initialize theme from localStorage or default to dark
        const savedTheme = localStorage.getItem('qumail_theme') || 'dark'
        document.body.classList.remove('theme-light', 'theme-dark')
        document.body.classList.add(`theme-${savedTheme}`)
    }, [])

    if (isLoading) {
        return (
            <div className="loading-screen">
                <div className="loading-spinner"></div>
                <p>Loading QuMail...</p>
            </div>
        )
    }

    return (
        <ToastProvider>
            <Router>
                <Routes>
                    {!isAuthenticated ? (
                        <>
                            <Route path="/login" element={<LoginScreen />} />
                            <Route path="*" element={<Navigate to="/login" replace />} />
                        </>
                    ) : (
                        <Route element={<Layout />}>
                            <Route path="/" element={<Navigate to="/inbox" replace />} />
                            <Route path="/inbox" element={<EmailList folder="INBOX" />} />
                            <Route path="/sent" element={<EmailList folder="SENT" />} />
                            <Route path="/drafts" element={<EmailList folder="DRAFTS" />} />
                            <Route path="/email/:messageId" element={<EmailView />} />
                            <Route path="/compose" element={<ComposeEmail />} />
                            <Route path="*" element={<Navigate to="/inbox" replace />} />
                        </Route>
                    )}
                </Routes>
            </Router>
        </ToastProvider>
    )
}

export default App
