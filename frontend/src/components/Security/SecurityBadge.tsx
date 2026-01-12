import { SECURITY_LEVELS, type SecurityLevel } from '../../types/email'
import './SecurityBadge.css'

interface Props {
    level: SecurityLevel
    size?: 'small' | 'medium' | 'large'
    showLabel?: boolean
}

export default function SecurityBadge({ level, size = 'medium', showLabel = false }: Props) {
    const info = SECURITY_LEVELS[level]

    return (
        <div
            className={`security-badge security-badge-${size} security-level-${level}`}
            title={info.description}
        >
            <span className="badge-icon">{info.icon}</span>
            {showLabel && <span className="badge-label">{info.name}</span>}
        </div>
    )
}
