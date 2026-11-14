class DomainError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DomainValidationError(DomainError):
    pass


class InvalidStateTransitionError(DomainError):
    pass
