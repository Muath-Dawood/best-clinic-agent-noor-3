import json
import pytest

from src.data.services import (
    coerce_service_identifiers_to_pm_si,
    WOMEN_SERVICES,
    MEN_SERVICES,
)
from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import (
    update_booking_context,
    check_availability,
)
from src.workflows.step_controller import StepController
import src.tools.booking_tool as booking_tool_module


class DummyWrapper:
    def __init__(self, ctx):
        self.context = ctx


def test_exact_women_title_maps():
    pm, matched, unknown = coerce_service_identifiers_to_pm_si(
        ["استشارة طبية - قسم النسائية"], prefer_gender="female"
    )
    assert pm == [WOMEN_SERVICES[0]["pm_si"]]
    assert not unknown


def test_bullet_copy_paste_maps():
    line = "• استشارة طبية - قسم النسائية - 100.00 ₪ (00:20)"
    pm, matched, unknown = coerce_service_identifiers_to_pm_si(
        [line], prefer_gender="female"
    )
    assert pm == [WOMEN_SERVICES[0]["pm_si"]]
    assert not unknown


def test_short_phrase_respects_gender():
    pm_f, _, _ = coerce_service_identifiers_to_pm_si(
        ["استشارة طبية"], prefer_gender="female"
    )
    pm_m, _, _ = coerce_service_identifiers_to_pm_si(
        ["استشارة طبية"], prefer_gender="male"
    )
    assert pm_f == [WOMEN_SERVICES[0]["pm_si"]]
    assert pm_m == [MEN_SERVICES[0]["pm_si"]]


def test_mens_followup_maps():
    pm, _, _ = coerce_service_identifiers_to_pm_si(
        ["مراجعة دورية"], prefer_gender="male"
    )
    assert pm == [MEN_SERVICES[3]["pm_si"]]


@pytest.mark.asyncio
async def test_female_flow_passes_gender_guard(monkeypatch):
    async def fake_times(date, services, gender):
        return [{"time": "10:00"}]

    monkeypatch.setattr(
        booking_tool_module.booking_tool, "get_available_times", fake_times
    )

    ctx = BookingContext(gender="female")
    wrapper = DummyWrapper(ctx)

    updates = {"selected_services_pm_si": ["استشارة طبية - قسم النسائية"]}
    res = await update_booking_context.on_invoke_tool(
        wrapper, json.dumps({"updates": updates})
    )
    StepController(ctx).apply_patch(res.ctx_patch)

    assert ctx.selected_services_pm_si == [WOMEN_SERVICES[0]["pm_si"]]
    assert ctx.next_booking_step == BookingStep.SELECT_DATE

    res2 = await check_availability.on_invoke_tool(
        wrapper, json.dumps({"date": "2025-08-25"})
    )
    assert "الخدمة المختارة غير متاحة لهذا القسم" not in res2.public_text
