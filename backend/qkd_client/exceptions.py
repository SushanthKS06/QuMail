"""
QKD Client Exceptions
"""


class KeyRequestError(Exception):
    """Base exception for key request failures."""
    pass


class KeyNotFoundError(KeyRequestError):
    """Key with specified ID not found."""
    pass


class KeyExhaustedError(KeyRequestError):
    """Key material exhausted or already consumed."""
    pass


class KeyManagerUnavailableError(KeyRequestError):
    """Key Manager service not reachable."""
    pass
