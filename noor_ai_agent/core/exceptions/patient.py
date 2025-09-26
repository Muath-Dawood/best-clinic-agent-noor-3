"""
Patient-related exceptions.
"""


class PatientLookupError(Exception):
    """Exception raised when patient lookup fails."""
    pass


class PatientNotFoundError(PatientLookupError):
    """Exception raised when a patient is not found in the system."""
    pass
