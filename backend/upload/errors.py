"""Shared upload validation exception (kept separate to avoid import cycles)."""


class ValidationError(Exception):
    """.code is machine-readable (goes in the JSON error field), .message
    is the human-readable string returned alongside it."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message
