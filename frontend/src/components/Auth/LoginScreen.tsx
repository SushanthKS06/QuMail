import { Shield, Mail } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import './LoginScreen.css'

export default function LoginScreen() {
    const { login } = useAuth()

    return (
        <div className="login-screen">
            <div className="login-container">
                <div className="login-header">
                    <div className="login-logo">
                        <Shield size={48} />
                    </div>
                    <h1>QuMail</h1>
                    <p className="login-tagline">Quantum Secure Email</p>
                </div>

                <div className="login-features">
                    <div className="feature">
                        <span className="feature-icon">🔐</span>
                        <div>
                            <strong>One-Time Pad</strong>
                            <p>Information-theoretic security</p>
                        </div>
                    </div>
                    <div className="feature">
                        <span className="feature-icon">🛡️</span>
                        <div>
                            <strong>Quantum-Aided AES</strong>
                            <p>QKD-derived encryption keys</p>
                        </div>
                    </div>
                    <div className="feature">
                        <span className="feature-icon">⚛️</span>
                        <div>
                            <strong>Post-Quantum Crypto</strong>
                            <p>Future-proof protection</p>
                        </div>
                    </div>
                </div>

                <div className="login-actions">
                    <button className="login-button gmail" onClick={login}>
                        <Mail size={20} />
                        <span>Continue with Gmail</span>
                    </button>
                </div>

                <p className="login-note">
                    Your emails are encrypted end-to-end. Email servers never see your content.
                </p>
            </div>

            <div className="login-bg-gradient"></div>
        </div>
    )
}
