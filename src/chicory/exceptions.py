from __future__ import annotations


class ChicoryError(Exception):
    """Base exception for Chicory."""


class TaskNotFoundError(ChicoryError):
    """Raised when a task is not registered."""


class ValidationError(ChicoryError):
    """Raised when input/output validation fails."""


class RetryError(ChicoryError):
    """Raised to trigger a task retry."""

    def __init__(
        self,
        retries: int | None = None,
        max_retries: int | None = None,
        countdown: float | None = None,
    ):
        self.retries = retries
        self.max_retries = max_retries
        self.countdown = countdown
        super().__init__(
            f"Retry requested with countdown={countdown} "
            f"(attempt {retries}/{max_retries})"
        )


class MaxRetriesExceededError(ChicoryError):
    """Raised when max retries are exhausted."""


class BackendNotConfiguredError(ChicoryError):
    """Raised when backend operations are attempted without a backend."""


class BrokerConnectionError(ChicoryError):
    """Raised when broker connection fails."""


class DbPoolExhaustedException(ChicoryError):
    """Raised when the database connection pool is exhausted."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class TaskFailedException(ChicoryError):
    """Raised when a task fails."""
