"""
Patient service for handling patient data and lookups.
"""

from typing import Optional, Dict, Any
from ...core.models.patient import Patient
from ...core.exceptions import PatientLookupError, PatientNotFoundError
from ...utils.phone import PhoneNumberParser
from ..external import ExternalAPIService


class PatientService:
    """Service for handling patient data and lookups."""

    def __init__(self, external_api: ExternalAPIService):
        self.external_api = external_api
        self.phone_parser = PhoneNumberParser()

    async def lookup_patient_by_whatsapp_id(self, chat_id: str) -> Optional[Patient]:
        """
        Look up patient by WhatsApp chat ID.

        Args:
            chat_id: WhatsApp chat ID

        Returns:
            Patient object if found, None otherwise
        """
        phone = self.phone_parser.parse_whatsapp_to_local_palestinian_number(chat_id)

        if not phone or not self.phone_parser.is_valid_palestinian_number(phone):
            return None

        try:
            data = await self.external_api.lookup_patient(phone)
            return Patient.from_api_response(data)
        except PatientNotFoundError:
            return None
        except Exception as e:
            raise PatientLookupError(f"Failed to lookup patient: {e}")

    async def lookup_patient_by_phone(self, phone: str) -> Optional[Patient]:
        """
        Look up patient by phone number.

        Args:
            phone: Phone number in various formats

        Returns:
            Patient object if found, None otherwise
        """
        normalized_phone = self.phone_parser.normalize_to_local_format(phone)

        if not normalized_phone or not self.phone_parser.is_valid_palestinian_number(normalized_phone):
            return None

        try:
            data = await self.external_api.lookup_patient(normalized_phone)
            return Patient.from_api_response(data)
        except PatientNotFoundError:
            return None
        except Exception as e:
            raise PatientLookupError(f"Failed to lookup patient: {e}")

    def create_new_patient(self, name: str, phone: str, gender: str) -> Patient:
        """
        Create a new patient instance.

        Args:
            name: Patient name
            phone: Patient phone number
            gender: Patient gender

        Returns:
            New Patient instance
        """
        return Patient.new_patient(name, phone, gender)

    def is_existing_patient(self, patient: Optional[Patient]) -> bool:
        """
        Check if patient is an existing patient in the system.

        Args:
            patient: Patient object to check

        Returns:
            True if existing patient, False otherwise
        """
        return patient is not None and patient.is_existing
