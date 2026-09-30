from __future__ import annotations


class BlockValidationError(ValueError):
    def __init__(self, message: str, *, path: str = "blocks") -> None:
        super().__init__(message)
        self.path = path
