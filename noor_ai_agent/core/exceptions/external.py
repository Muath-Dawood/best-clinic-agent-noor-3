"""
External API-related exceptions.
"""


class ExternalAPIError(Exception):
    """Base exception for external API errors."""
    pass


class WhatsAppAPIError(ExternalAPIError):
    """Exception raised when WhatsApp API calls fail."""
    pass
