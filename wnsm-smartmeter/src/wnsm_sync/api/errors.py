"""WN Smart Meter API Errors."""
import logging

logger = logging.getLogger(__name__)


class WNSMApiError(Exception):
    """Generic error for WNSM API."""

    def __init__(self, msg, code=None, error_response=""):
        self.code = code or 0
        self.error_response = error_response
        super().__init__(msg)

    @property
    def msg(self):
        return self.args[0]


class AuthenticationError(WNSMApiError):
    """Raised when authentication fails."""


class MeteringPointNotFoundError(WNSMApiError):
    """Raised when a metering point is not found."""
