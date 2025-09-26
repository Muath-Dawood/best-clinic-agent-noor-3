"""
Patient-related data models.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PatientDetails(BaseModel):
    """Patient details from the clinic database."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    pm_si: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class Patient(BaseModel):
    """Complete patient model."""

    model_config = ConfigDict(extra="forbid")

    details: PatientDetails
    appointments: List[Dict[str, Any]] = Field(default_factory=list)
    is_existing: bool = True

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Patient":
        """Create Patient from API response."""
        details_data = data.get("details", {})
        appointments_data = data.get("appointments", {}).get("data", [])

        return cls(
            details=PatientDetails(**details_data),
            appointments=appointments_data,
            is_existing=True,
        )

    @classmethod
    def new_patient(cls, name: str, phone: str, gender: str) -> "Patient":
        """Create a new patient instance."""
        return cls(
            details=PatientDetails(
                name=name,
                phone=phone,
                gender=gender,
            ),
            appointments=[],
            is_existing=False,
        )
