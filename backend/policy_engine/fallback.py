import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_fallback_level(
    requested_level: int,
    recipient_capabilities: List[Dict[str, Any]],
) -> int:
    if not recipient_capabilities:
        return requested_level
    
    common_levels = set([1, 2, 3, 4])
    for cap in recipient_capabilities:
        supported = set(cap.get("supported_levels", [4]))
        common_levels &= supported
    
    if not common_levels:
        logger.warning("No common security levels, falling back to plain")
        return 4
    
    if 4 in common_levels:
        common_levels.discard(4)
        if not common_levels:
            return 4
    
    fallback_order = {
        1: [1, 2, 3, 4],
        2: [2, 3, 4],
        3: [3, 2, 4],
        4: [4],
    }
    
    order = fallback_order.get(requested_level, [requested_level, 4])
    
    for level in order:
        if level in common_levels or level == 4:
            return level
    
    return 4


def should_warn_downgrade(original: int, actual: int) -> bool:
    return original < actual or (original < 4 and actual == 4)


def get_downgrade_message(original: int, actual: int) -> str:
    level_names = {
        1: "Quantum Secure OTP",
        2: "Quantum-Aided AES",
        3: "Post-Quantum Crypto",
        4: "No Security (Plain)",
    }
    
    return (
        f"Security level changed from {level_names.get(original, original)} "
        f"to {level_names.get(actual, actual)}. "
        f"This may affect the security of your communication."
    )
