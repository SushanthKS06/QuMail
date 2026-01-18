import { useState, useEffect } from 'react'
import { X, Moon, Sun, Shield, User } from 'lucide-react'
import { getSettings, updateSettings } from '../../api/settings'
import { useToast } from '../Toast/Toast'
import './SettingsModal.css'

interface SettingsModalProps {
    isOpen: boolean
    onClose: () => void
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const { addToast } = useToast()
    const [theme, setTheme] = useState<'light' | 'dark'>('dark')
    const [securityLevel, setSecurityLevel] = useState<number>(2)

    useEffect(() => {
        if (isOpen) {
            loadSettings()
        }
    }, [isOpen])

    async function loadSettings() {
        try {
            const settings = await getSettings()
            // Ensure values are valid or fallback
            setTheme(settings.theme === 'light' ? 'light' : 'dark')
            setSecurityLevel(settings.security_level || 2)
        } catch (error) {
            console.error('Failed to load settings:', error)
            // Silent error or toast?
        }
    }

    async function handleThemeChange(newTheme: 'light' | 'dark') {
        const oldTheme = theme
        setTheme(newTheme) // Optimistic update
        updateBodyClass(newTheme)
        localStorage.setItem('qumail_theme', newTheme) // Persist to localStorage

        try {
            await updateSettings({ theme: newTheme, security_level: securityLevel })
            addToast(`Switched to ${newTheme} mode`, 'success')
        } catch (error) {
            console.error('Failed to save theme:', error)
            setTheme(oldTheme)
            updateBodyClass(oldTheme)
            localStorage.setItem('qumail_theme', oldTheme)
            addToast('Failed to save theme', 'error')
        }
    }

    async function handleSecurityLevelChange(level: number) {
        setSecurityLevel(level) // Optimistic

        try {
            await updateSettings({ theme, security_level: level })
        } catch (error) {
            console.error('Failed to save security level:', error)
            // Revert? simpler to just toast error
            addToast('Failed to save security level', 'error')
        }
    }

    function updateBodyClass(theme: string) {
        document.body.classList.remove('theme-light', 'theme-dark')
        document.body.classList.add(`theme-${theme}`)
    }

    if (!isOpen) return null

    return (
        <div className="settings-overlay" onClick={onClose}>
            <div className="settings-modal" onClick={e => e.stopPropagation()}>
                <div className="settings-header">
                    <h2>Settings</h2>
                    <button className="close-button" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="settings-content">
                    <section className="settings-section">
                        <h3><User size={18} /> Account</h3>
                        <div className="settings-item">
                            <label>Current Account</label>
                            <div className="account-info">
                                <span className="email-badge">user@gmail.com</span>
                                <span className="provider-badge">Gmail (OAuth)</span>
                            </div>
                        </div>
                    </section>

                    <section className="settings-section">
                        <h3><Moon size={18} /> Appearance</h3>
                        <div className="settings-item">
                            <label>Theme</label>
                            <div className="theme-toggle">
                                <button
                                    className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
                                    onClick={() => handleThemeChange('dark')}
                                >
                                    <Moon size={16} /> Dark
                                </button>
                                <button
                                    className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
                                    onClick={() => handleThemeChange('light')}
                                >
                                    <Sun size={16} /> Light
                                </button>
                            </div>
                        </div>
                    </section>

                    <section className="settings-section">
                        <h3><Shield size={18} /> Security</h3>
                        <div className="settings-item">
                            <label>Default Security Level</label>
                            <select
                                className="security-select"
                                value={securityLevel}
                                onChange={(e) => handleSecurityLevelChange(Number(e.target.value))}
                            >
                                <option value="1">Standard (AES)</option>
                                <option value="2">Quantum-Aided (AES+QKD)</option>
                                <option value="3">Information-Theoretic (OTP)</option>
                            </select>
                        </div>
                    </section>
                </div>

                <div className="settings-footer">
                    <span className="version">QuMail v1.0.0</span>
                </div>
            </div>
        </div>
    )
}
