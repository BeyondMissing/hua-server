
class SuitingError(ValueError):
    """A persisted suit operation rejected by the game rules."""
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = int(status)
        