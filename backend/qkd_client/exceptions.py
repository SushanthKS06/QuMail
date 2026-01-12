class KeyRequestError(Exception):
    pass


class KeyNotFoundError(KeyRequestError):
    pass


class KeyExhaustedError(KeyRequestError):
    pass


class KeyManagerUnavailableError(KeyRequestError):
    pass
