from types import SimpleNamespace
from types import SimpleNamespace
from src.tools.booking_agent_tool import _build_booking_idempotency_key


def _ctx(chat, date, time, emp, svcs):
    return SimpleNamespace(chat_id=chat, appointment_date=date, appointment_time=time, employee_pm_si=emp, selected_services_pm_si=svcs)


def test_idempotency_differs_by_slot_and_doctor():
    a = _build_booking_idempotency_key(_ctx("c1", "2025-09-01", "10:00", "e1", ["s1", "s2"]))
    b = _build_booking_idempotency_key(_ctx("c1", "2025-09-01", "10:00", "e2", ["s1", "s2"]))
    c = _build_booking_idempotency_key(_ctx("c1", "2025-09-01", "11:00", "e1", ["s1", "s2"]))
    d = _build_booking_idempotency_key(_ctx("c1", "2025-09-01", "10:00", "e1", ["s2", "s1"]))
    assert a != b and a != c and a == d
