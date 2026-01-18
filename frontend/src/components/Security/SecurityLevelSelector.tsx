import { SECURITY_LEVELS, type SecurityLevel } from '../../types/email'
import { useSecurityStatus } from '../../hooks/useSecurityStatus'
import './SecurityLevelSelector.css'

interface Props {
    value: SecurityLevel
    onChange: (level: SecurityLevel) => void
}

export default function SecurityLevelSelector({ value, onChange }: Props) {
    const { status } = useSecurityStatus()

    const levels: SecurityLevel[] = [1, 2, 3, 4]

    function isLevelAvailable(level: SecurityLevel): boolean {
        if (level === 4) return true
        if (!status?.km_connected) return false
        if (level === 1 && (status.available_key_material.otp_bytes || 0) < 1000) return false
        if (level === 2 && (status.available_key_material.aes_keys || 0) < 1) return false
        return true
    }

    return (
        <div className="security-selector">
            {levels.map((level) => {
                const info = SECURITY_LEVELS[level]
                const available = isLevelAvailable(level)
                const selected = value === level

                return (
                    <button
                        key={level}
                        className={`level-option level-${level} ${selected ? 'selected' : ''} ${!available ? 'disabled' : ''}`}
                        onClick={() => available && onChange(level)}
                        disabled={!available}
                        title={`${info.name}\n${info.description}`}
                    >
                        {/* <span className="level-icon">{info.icon}</span> */}
                        <span className="level-name">{info.name}</span>
                        {info.quantum_safe && (
                            <span className="quantum-badge">Q-Safe</span>
                        )}
                    </button>
                )
            })}
        </div>
    )
}


