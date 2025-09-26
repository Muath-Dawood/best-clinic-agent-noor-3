"""
Custom exceptions for the Noor AI Agent system.
"""

from .booking import BookingFlowError, BookingValidationError, SlotUnavailableError
from .patient import PatientLookupError, PatientNotFoundError
from .external import ExternalAPIError, WhatsAppAPIError

__all__ = [
    "BookingFlowError",
    "BookingValidationError",
    "SlotUnavailableError",
    "PatientLookupError",
    "PatientNotFoundError",
    "ExternalAPIError",
    "WhatsAppAPIError",
]
