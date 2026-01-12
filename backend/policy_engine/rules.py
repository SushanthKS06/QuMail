"""
Security Rules

Defines security rules and constraints for the policy engine.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LevelRequirements:
    """Requirements for a security level."""
    level: int
    name: str
    requires_km: bool
    requires_recipient_key: bool
    max_message_size: Optional[int]
    description: str


class SecurityRules:
    """
    Security rules for email encryption.
    
    Defines what is required for each security level
    and constraints on their use.
    """
    
    LEVEL_REQUIREMENTS = {
        1: LevelRequirements(
            level=1,
            name="Quantum Secure OTP",
            requires_km=True,
            requires_recipient_key=False,
            max_message_size=1024 * 1024,
            description="One-Time Pad with QKD keys",
        ),
        2: LevelRequirements(
            level=2,
            name="Quantum-Aided AES",
            requires_km=True,
            requires_recipient_key=False,
            max_message_size=None,
            description="AES-256-GCM with QKD-derived keys",
        ),
        3: LevelRequirements(
            level=3,
            name="Post-Quantum Crypto",
            requires_km=True,
            requires_recipient_key=True,
            max_message_size=None,
            description="Kyber + Dilithium hybrid encryption",
        ),
        4: LevelRequirements(
            level=4,
            name="No Security",
            requires_km=False,
            requires_recipient_key=False,
            max_message_size=None,
            description="Plain text email",
        ),
    }
    
    def __init__(self):
        self.allow_fallback = True
        self.default_level = 2
        self.require_encryption_for_attachments = False
    
    def get_requirements(self, level: int) -> LevelRequirements:
        """Get requirements for a security level."""
        return self.LEVEL_REQUIREMENTS.get(level)
    
    def can_use_level(
        self,
        level: int,
        km_connected: bool,
        has_recipient_key: bool,
        message_size: int,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a security level can be used.
        
        Args:
            level: Security level to check
            km_connected: Whether Key Manager is connected
            has_recipient_key: Whether recipient's public key is available
            message_size: Total message size in bytes
        
        Returns:
            Tuple of (can_use, reason_if_not)
        """
        req = self.get_requirements(level)
        if not req:
            return False, f"Invalid security level: {level}"
        
        if req.requires_km and not km_connected:
            return False, "Key Manager not connected"
        
        if req.requires_recipient_key and not has_recipient_key:
            return False, "Recipient's public key not available"
        
        if req.max_message_size and message_size > req.max_message_size:
            return False, f"Message too large for level {level} (max: {req.max_message_size} bytes)"
        
        return True, None
    
    def get_available_levels(
        self,
        km_connected: bool,
        has_recipient_key: bool,
    ) -> List[int]:
        """Get list of available security levels."""
        available = [4]
        
        if km_connected:
            available.append(2)
            available.append(1)
            
            if has_recipient_key:
                available.append(3)
        
        return sorted(available)
