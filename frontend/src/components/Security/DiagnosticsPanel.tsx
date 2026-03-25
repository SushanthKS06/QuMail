import { useState } from 'react'
import { Shield, CheckCircle, XCircle, Loader, Play, Clock } from 'lucide-react'
import { type TestResult } from '../../api/security'
import { getAuthToken } from '../../api/client'
import './DiagnosticsPanel.css'

interface StreamingResult {
    tests: TestResult[]
    overall_success: boolean | null
    total_duration_ms: number | null
    isComplete: boolean
}

export default function DiagnosticsPanel() {
    const [isRunning, setIsRunning] = useState(false)
    const [result, setResult] = useState<StreamingResult | null>(null)
    const [error, setError] = useState<string | null>(null)

    async function handleRunDiagnostics() {
        setIsRunning(true)
        setError(null)
        setResult({ tests: [], overall_success: null, total_duration_ms: null, isComplete: false })

        try {
            const token = getAuthToken()
            const response = await fetch('/api/v1/diagnostics/run/stream', {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            })

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }

            const reader = response.body?.getReader()
            const decoder = new TextDecoder()

            if (!reader) {
                throw new Error('No response body')
            }

            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n\n')
                buffer = lines.pop() || ''

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6)
                        try {
                            const event = JSON.parse(jsonStr)

                            if (event.type === 'test_result') {
                                setResult(prev => ({
                                    ...prev!,
                                    tests: [...(prev?.tests || []), event.result],
                                }))
                            } else if (event.type === 'complete') {
                                setResult(prev => ({
                                    ...prev!,
                                    overall_success: event.overall_success,
                                    total_duration_ms: event.total_duration_ms,
                                    isComplete: true,
                                }))
                            }
                        } catch (e) {
                            console.error('Failed to parse event:', e)
                        }
                    }
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to run diagnostics')
        } finally {
            setIsRunning(false)
        }
    }

    function getSecurityLevelIcon(level: number): string {
        switch (level) {
            case 1: return '🔐'
            case 2: return '🛡️'
            case 3: return '⚛️'
            default: return '📧'
        }
    }

    const pendingTests = ['otp', 'aes', 'pqc', 'attachment']
    const completedCount = result?.tests.length || 0

    return (
        <div className="diagnostics-panel">
            <div className="diagnostics-header">
                <div className="diagnostics-title">
                    <Shield size={24} />
                    <h3>Security Diagnostics</h3>
                </div>
                <p className="diagnostics-description">
                    Test encryption and decryption operations for all security levels to verify system integrity.
                </p>
            </div>

            <button
                className={`run-diagnostics-btn ${isRunning ? 'running' : ''}`}
                onClick={handleRunDiagnostics}
                disabled={isRunning}
            >
                {isRunning ? (
                    <>
                        <Loader size={18} className="spinning" />
                        <span>Running Tests... ({completedCount}/4)</span>
                    </>
                ) : (
                    <>
                        <Play size={18} />
                        <span>Run Security Diagnostics</span>
                    </>
                )}
            </button>

            {error && (
                <div className="diagnostics-error">
                    <XCircle size={18} />
                    <span>{error}</span>
                </div>
            )}

            {result && (
                <div className="diagnostics-results">
                    {result.isComplete ? (
                        <div className={`overall-result ${result.overall_success ? 'success' : 'failure'}`}>
                            {result.overall_success ? (
                                <>
                                    <CheckCircle size={24} />
                                    <span>All Tests Passed</span>
                                </>
                            ) : (
                                <>
                                    <XCircle size={24} />
                                    <span>Some Tests Failed</span>
                                </>
                            )}
                            <span className="total-time">{result.total_duration_ms?.toFixed(2)}ms</span>
                        </div>
                    ) : (
                        <div className="overall-result running">
                            <Loader size={24} className="spinning" />
                            <span>Running Tests...</span>
                            <span className="total-time">{completedCount}/4 complete</span>
                        </div>
                    )}

                    <div className="test-cards">
                        {result.tests.map((test, index) => (
                            <TestCard
                                key={index}
                                test={test}
                                icon={getSecurityLevelIcon(test.security_level)}
                                isNew={index === result.tests.length - 1 && !result.isComplete}
                            />
                        ))}

                        {/* Show pending test placeholders */}
                        {isRunning && pendingTests.slice(completedCount).map((testId, index) => (
                            <PendingCard key={`pending-${index}`} testId={testId} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

function TestCard({ test, icon, isNew }: { test: TestResult; icon: string; isNew?: boolean }) {
    return (
        <div className={`test-card ${test.success ? 'success' : 'failure'} ${isNew ? 'animate-in' : ''}`}>
            <div className="test-card-header">
                <span className="test-icon">{icon}</span>
                <span className="test-name">{test.test_name}</span>
                {test.success ? (
                    <CheckCircle size={20} className="status-icon success" />
                ) : (
                    <XCircle size={20} className="status-icon failure" />
                )}
            </div>
            <div className="test-card-body">
                <p className="test-message">{test.message}</p>
                <div className="test-meta">
                    <span className="test-level">Level {test.security_level}</span>
                    <span className="test-time">{test.duration_ms.toFixed(2)}ms</span>
                </div>
                {test.details && (
                    <div className="test-details">
                        {Object.entries(test.details).map(([key, value]) => (
                            <span key={key} className="detail-item">
                                {key.replace(/_/g, ' ')}: {value}
                            </span>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

function PendingCard({ testId }: { testId: string }) {
    const testNames: Record<string, string> = {
        otp: 'One-Time Pad (OTP)',
        aes: 'AES-256-GCM',
        pqc: 'Post-Quantum Crypto',
        attachment: 'Attachment Encryption',
    }

    const testIcons: Record<string, string> = {
        otp: '🔐',
        aes: '🛡️',
        pqc: '⚛️',
        attachment: '📎',
    }

    return (
        <div className="test-card pending">
            <div className="test-card-header">
                <span className="test-icon">{testIcons[testId]}</span>
                <span className="test-name">{testNames[testId]}</span>
                <Clock size={20} className="status-icon pending" />
            </div>
            <div className="test-card-body">
                <p className="test-message">Waiting...</p>
            </div>
        </div>
    )
}
