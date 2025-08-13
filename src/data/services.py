"""
Hard-coded bookable services for Best Clinic 24.
This eliminates the need to call the categories API during booking flow.
"""

from typing import Optional
from typing import List, Tuple

from src.app.context_models import BookingContext

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


def get_services_by_gender(gender: str) -> list:
    """Get services based on gender preference."""
    if gender.lower() in ['male', 'men', 'ذكر', 'رجال']:
        return MEN_SERVICES
    elif gender.lower() in ['female', 'women', 'أنثى', 'نساء']:
        return WOMEN_SERVICES
    else:
        # Default to men's services if gender unclear
        return MEN_SERVICES


def get_cus_sec_pm_si_by_gender(gender: str) -> str:
    """Get the appropriate cus_sec_pm_si token based on gender."""
    if gender.lower() in ['male', 'men', 'ذكر', 'رجال']:
        return MEN_CUS_SEC_PM_SI
    elif gender.lower() in ['female', 'women', 'أنثى', 'نساء']:
        return WOMEN_CUS_SEC_PM_SI
    else:
        return MEN_CUS_SEC_PM_SI


def find_service_by_pm_si(pm_si: str) -> dict | None:
    """Find a service by its pm_si token across all services."""
    all_services = MEN_SERVICES + WOMEN_SERVICES
    for service in all_services:
        if service['pm_si'] == pm_si:
            return service
    return None

def list_all_services() -> list:
    """Return a flat list of all services."""
    return MEN_SERVICES + WOMEN_SERVICES


def coerce_service_identifiers_to_pm_si(identifiers: List[str]) -> Tuple[List[str], list, List[str]]:
    """
    Accept a mixed list of pm_si tokens OR human titles/bullets and
    return:
      - pm_si_list: canonical pm_si tokens
      - matched_services: list of full service dicts (parallel)
      - unknown: any identifiers we couldn't map
    """
    all_services = list_all_services()
    pm_si_list: List[str] = []
    matched: list = []
    unknown: List[str] = []

    for raw in identifiers or []:
        if not isinstance(raw, str) or not raw.strip():
            unknown.append(str(raw))
            continue

    # Trim and normalize string
        s = str(raw).strip()
        # 1) already a pm_si?
        svc = next((x for x in all_services if x['pm_si'] == s), None)
        if svc:
            pm_si_list.append(svc['pm_si'])
            matched.append(svc)
            continue

        # 2) strip bullet formatting
        core = s
        if ' - ' in core:
            core = core.split(' - ', 1)[0].strip()
        if core.startswith('•'):
            core = core.lstrip('•').strip()

        # 3) try exact or contains match on title / title_en
        svc = next(
            (
                x
                for x in all_services
                if x['title'] == core
                or (x.get('title_en') and x['title_en'] == core)
                or core in x['title']
                or (x.get('title_en') and core in x['title_en'])
            ),
            None,
        )
        if svc:
            pm_si_list.append(svc['pm_si'])
            matched.append(svc)
        else:
            unknown.append(s)

    return pm_si_list, matched, unknown



def get_service_summary(services: list, ctx: Optional[BookingContext] = None) -> str:
    """Get a human-readable summary of services for display."""
    if not services:
        return "لا توجد خدمات متاحة"

    currency = (ctx.price_currency if ctx and ctx.price_currency else "NIS").upper()
    symbol_map = {
        "NIS": "₪",
        "ILS": "₪",
        "KWD": "د.ك",
        "USD": "$",
        "EUR": "€",
    }
    symbol = symbol_map.get(currency, "₪")

    summaries = []
    for service in services:
        price = service['price']
        duration = service['duration']
        title = service['title']
        summaries.append(f"• {title} - {price} {symbol} ({duration})")

    return "\n".join(summaries)
