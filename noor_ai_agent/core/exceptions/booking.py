"""
Booking-related exceptions.
"""


class BookingFlowError(Exception):
    """Base exception for booking flow errors."""
    pass


class BookingValidationError(BookingFlowError):
    """Exception raised when booking validation fails."""
    pass


class SlotUnavailableError(BookingFlowError):
    """Exception raised when a booking slot is no longer available."""
    pass
