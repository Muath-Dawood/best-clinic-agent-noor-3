"""
Service data provider for clinic services.
"""

from typing import List, Dict, Optional, Tuple
from ..external import ExternalAPIService
from ...core.models.booking import Service
from ...core.enums import Gender


class ServiceDataProvider:
    """Provides service data for the booking system."""

    # Men's services (using men's cus_sec_pm_si)
    MEN_SERVICES = [
        {
            "title": "استشارة طبية - ضعف الانتصاب وصحة الذكورة",
            "title_en": "Medical Consultation - Erectile Dysfunction & Men's Health",
            "duration": "00:30",
            "duration_minutes": 30,
            "pm_si": "a25ZYU0yS21HQU43WUxBT3VHa3hyMVl2d0JoTllWMjZzU2IzTVBHS2VLeVVBMW01MHBVWHFGWGxYY1FSWnExZAsdgn352FCSzv2414sdgn352FCSzv2414",
            "price": "100.00",
            "price_numeric": 100.00,
            "category": "consultation"
        },
        {
            "title": "جلسة علاجية - موجات تصادمية خطية",
            "title_en": "Therapeutic Session - Linear Shockwave Therapy",
            "duration": "00:40",
            "duration_minutes": 40,
            "pm_si": "LzVmL2VhcUdldUU2WC8vTVJsL0toMU1KSU5MNkdzZEtxdFRTZE5HM1JqQ3Yxa3daVnQyU1dMTE9QQ3lLUTN3cwsdgn352FCSzv2414sdgn352FCSzv2414",
            "price": "4800.00",
            "price_numeric": 4800.00,
            "category": "therapy"
        },
        {
            "title": "جلسة علاجية - حقن الفيلر",
            "title_en": "Therapeutic Session - Filler Injection",
            "duration": "00:45",
            "duration_minutes": 45,
            "pm_si": "RXpIc2h5WUV3TjFmNExBZVFaRFJLbkR5cFpOSWEwN3d2OFk5MGJIVU9MQU1nMGFPb01iT3NvekNRUWZGTGRBVwsdgn352FCSzv2414sdgn352FCSzv2414",
            "price": "3500.00",
            "price_numeric": 3500.00,
            "category": "therapy"
        },
        {
            "title": "مراجعة دورية",
            "title_en": "Regular Follow-up",
            "duration": "00:30",
            "duration_minutes": 30,
            "pm_si": "VHJ0eTVlWDl6TjdvV2QrTG1NWk9INEJ5L2V6dU9pWkc2NVd4cWk2YmlWbVhQODZqYVpyb2NaK1BDaVp6eXpGWQsdgn352FCSzv2414sdgn352FCSzv2414",
            "price": "50.00",
            "price_numeric": 50.00,
            "category": "followup"
        }
    ]

    # Women's services (using women's cus_sec_pm_si)
    WOMEN_SERVICES = [
        {
            "title": "استشارة طبية - قسم النسائية",
            "title_en": "Medical Consultation - Gynecology Department",
            "duration": "00:20",
            "duration_minutes": 20,
            "pm_si": "VnI3YWEwdDA1cDdxRW5PVmhXQ2RaRElFSlF2ZFdMUXdWRVQ4ZG5jY2lnT1ZqNmF4NDRkZ29CQmVmV3QvdjNNSwsdgn352FCSzv2414sdgn352FCSzv2414",
            "price": "100.00",
            "price_numeric": 100.00,
            "category": "consultation"
        },
        {
            "title": "مراجعة دورية",
            "title_en": "Regular Follow-up",
            "duration": "00:30",
            "duration_minutes": 30,
            "pm_si": "OVdLSXVsaTNnTVBJVGVvVkVUMnhIZXNqZ043NXlJMjlxeWRHV1FuUEhSMElKbFRaWDlPOGMwR1NheTNoQlNObwsdgn352FCSzv2414sdgn352FCSzv2414",
            "price": "80.00",
            "price_numeric": 80.00,
            "category": "followup"
        }
    ]

    # Static tokens for each section
    MEN_CUS_SEC_PM_SI = "Z2lSQ2ZFTEJBcFVXR2MrSUkra3pyN3l1N0NpV0dnS0tHVEJwZVdSTDlkY3k3Qm5RU2tFcEdFOXI1MnJiUWtsSTRjV2VsTmcvYlFIcjhDOUZ0dy94Ync9PQsdgn352FCSzv2414sdgn352FCSzv2414"
    WOMEN_CUS_SEC_PM_SI = "a25ZYU0yS21HQU43WUxBT3VHa3hyNUJzRHRzUGppdm5CM0RBR2twb1NHRFhrM1doT3BOcGlFZ3g5WkRBYWxkM0x4Ymo0RUl3MGRMNlgzaHBKekpTc2c9PQsdgn352FCSzv2414sdgn352FCSzv2414"

    def __init__(self, external_api: ExternalAPIService):
        self.external_api = external_api

    def get_services_by_gender(self, gender: Gender) -> List[Dict]:
        """Get services based on gender preference."""
        if gender == Gender.MALE:
            return self.MEN_SERVICES.copy()
        elif gender == Gender.FEMALE:
            return self.WOMEN_SERVICES.copy()
        else:
            # Default to men's services if gender unclear
            return self.MEN_SERVICES.copy()

    def get_cus_sec_pm_si_by_gender(self, gender: Gender) -> str:
        """Get the appropriate cus_sec_pm_si token based on gender."""
        if gender == Gender.MALE:
            return self.MEN_CUS_SEC_PM_SI
        elif gender == Gender.FEMALE:
            return self.WOMEN_CUS_SEC_PM_SI
        else:
            return self.MEN_CUS_SEC_PM_SI

    def find_service_by_pm_si(self, pm_si: str) -> Optional[Dict]:
        """Find a service by its pm_si token across all services."""
        all_services = self.MEN_SERVICES + self.WOMEN_SERVICES
        for service in all_services:
            if service['pm_si'] == pm_si:
                return service
        return None

    def list_all_services(self) -> List[Dict]:
        """Return a flat list of all services."""
        return self.MEN_SERVICES + self.WOMEN_SERVICES

    def coerce_service_identifiers_to_pm_si(
        self,
        identifiers: List[str],
        prefer_gender: Optional[Gender] = None
    ) -> Tuple[List[str], List[Dict], List[str]]:
        """
        Map human-friendly service identifiers to canonical pm_si tokens.

        Args:
            identifiers: Raw service identifiers such as titles, bullet lines, or pm_si tokens
            prefer_gender: Optional gender hint to bias lookup order toward the corresponding catalog

        Returns:
            Tuple of (pm_si_list, matched_services, unknown_identifiers)
        """
        all_services = self.list_all_services()
        pm_si_list: List[str] = []
        matched: List[Dict] = []
        unknown: List[str] = []

        # Minimal Arabic synonym map for women's services (expandable)
        WOMEN_SYNONYMS = {
            "قسم النسائية": "قسم النسائية",
            "الصحة النسائية": "قسم النسائية",
            "النسائية": "قسم النسائية",
            "استشارة طبية - الصحة النسائية": "استشارة طبية - قسم النسائية",
            "استشارة - الصحة النسائية": "استشارة طبية - قسم النسائية",
            "استشارة نسائية": "استشارة طبية - قسم النسائية",
        }

        def catalogs_by_gender() -> List[List[Dict]]:
            if prefer_gender == Gender.FEMALE:
                return [self.WOMEN_SERVICES, self.MEN_SERVICES]
            return [self.MEN_SERVICES, self.WOMEN_SERVICES]

        def try_match_one(s: str) -> Optional[Dict]:
            """Attempt to resolve a single identifier to a service dict."""
            # 1) exact pm_si
            svc = next((x for x in all_services if x["pm_si"] == s), None)
            if svc:
                return svc

            # Normalize via synonyms on full string first
            s_norm = WOMEN_SYNONYMS.get(s, s)

            # 2) exact title match (gender-aware search order)
            for catalog in catalogs_by_gender():
                svc = next(
                    (x for x in catalog if x["title"] == s_norm or x.get("title_en") == s_norm),
                    None,
                )
                if svc:
                    return svc

            # 3) strip bullet + trailing price if present
            import re
            m = re.match(r"^\s*•?\s*(?P<title>.+?)\s+-\s+\d", s_norm)
            core = m.group("title").strip() if m else s_norm

            # Apply synonyms again on the core
            core = WOMEN_SYNONYMS.get(core, core)

            # 4) exact core match (gender-aware)
            for catalog in catalogs_by_gender():
                svc = next(
                    (x for x in catalog if x["title"] == core or x.get("title_en") == core),
                    None,
                )
                if svc:
                    return svc

            # 5) contains match (gender-aware)
            for catalog in catalogs_by_gender():
                svc = next(
                    (
                        x
                        for x in catalog
                        if core in x["title"]
                        or (x.get("title_en") and core in x["title_en"])
                    ),
                    None,
                )
                if svc:
                    return svc

            return None

        for raw in identifiers or []:
            if not isinstance(raw, str) or not raw.strip():
                unknown.append(str(raw))
                continue

            s = str(raw).strip()
            svc = try_match_one(s)
            if svc:
                pm_si_list.append(svc["pm_si"])
                matched.append(svc)
            else:
                unknown.append(s)

        return pm_si_list, matched, unknown

    def get_service_summary(self, services: List[Dict], currency: str = "NIS") -> str:
        """Get a human-readable summary of services for display."""
        if not services:
            return "لا توجد خدمات متاحة"

        symbol_map = {
            "NIS": "₪",
            "ILS": "₪",
            "KWD": "د.ك",
            "USD": "$",
            "EUR": "€",
        }
        symbol = symbol_map.get(currency.upper(), "₪")

        summaries = []
        for service in services:
            price = service['price']
            duration = service['duration']
            title = service['title']
            summaries.append(f"• {title} - {price} {symbol} ({duration})")

        return "\n".join(summaries)
