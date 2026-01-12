import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
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
    )
}

export default App
