"""
Booking Agent Tool - provides functional tools for Noor to handle appointment booking.
Uses the correct @function_tool pattern from Agents SDK.
"""

from typing import List, Dict, Optional, Literal
import json
from pydantic import BaseModel, ConfigDict
from agents import function_tool, RunContextWrapper

from src.tools.booking_tool import booking_tool, BookingFlowError
from src.data.services import get_services_by_gender
from src.app.context_models import (
    BookingContext,
    BookingStep,
    BOOKING_STEP_TRANSITIONS,
)
from src.tools.tool_result import ToolResult
from src.workflows.step_controller import StepController


class BookingContextUpdate(BaseModel):
    """Subset of :class:`BookingContext` fields that can be updated."""

    model_config = ConfigDict(extra="forbid")

    selected_services_pm_si: Optional[List[str]] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    employee_pm_si: Optional[str] = None
    employee_name: Optional[str] = None
    gender: Optional[str] = None
    next_booking_step: Optional[BookingStep] = None


def _validate_step(
    ctx: BookingContext, *allowed: Optional[BookingStep]
) -> Optional[str]:
    """Ensure the booking flow is currently in one of ``allowed`` steps."""
    if ctx.next_booking_step not in allowed:
        return "عذراً، لا يمكن تنفيذ هذه الخطوة الآن."
    return None


def normalize_gender(gender: Optional[str]) -> str:
    """Convert gender to English for API ('male'/'female')."""
    if not gender:
        return "male"
    gender = gender.strip().lower()
    if gender in ["male", "ذكر", "m", "رجال"]:
        return "male"
    if gender in ["female", "أنثى", "f", "نساء"]:
        return "female"
    return "male"  # fallback


@function_tool
async def suggest_services(wrapper: RunContextWrapper[BookingContext]) -> ToolResult:
    """Show available services based on the user's gender preference."""
    ctx = wrapper.context

    error = _validate_step(ctx, None, BookingStep.SELECT_SERVICE)
    if error:
        return ToolResult(public_text=error, ctx_patch={}, version=ctx.version)

    gender = ctx.gender or "male"

    try:
        services = get_services_by_gender(gender)
        if not services:
            return ToolResult(
                public_text="عذراً، لا توجد خدمات متاحة لهذا القسم حالياً.",
                ctx_patch={},
                version=ctx.version,
            )

        patch = {
            "selected_services_data": services,
            "next_booking_step": BOOKING_STEP_TRANSITIONS[None][0],
        }

        return ToolResult(
            public_text=json.dumps(services, ensure_ascii=False),
            ctx_patch=patch,
            private_data=services,
            version=ctx.version,
        )
    except Exception as e:
        return ToolResult(
            public_text=f"عذراً، حدث خطأ في جلب الخدمات: {str(e)}",
            ctx_patch={},
            version=ctx.version,
        )


@function_tool
async def check_availability(
    wrapper: RunContextWrapper[BookingContext], date: str
) -> ToolResult:
    """Get available times for a specific date."""

    ctx = wrapper.context

    error = _validate_step(ctx, BookingStep.SELECT_DATE)
    if error:
        return ToolResult(public_text=error, ctx_patch={}, version=ctx.version)

    if not ctx.selected_services_pm_si:
        return ToolResult(public_text="عذراً، يجب اختيار الخدمات أولاً.", ctx_patch={}, version=ctx.version)

    if not date:
        return ToolResult(public_text="عذراً، يجب تحديد التاريخ أولاً.", ctx_patch={}, version=ctx.version)

    parsed_date = booking_tool.parse_natural_date(date, ctx.user_lang or "ar")
    date = parsed_date or date

    gender = ctx.gender or "male"

    try:
        slots = await booking_tool.get_available_times(
            date, ctx.selected_services_pm_si, gender
        )
        if not slots:
            return ToolResult(
                public_text=f"عذراً، لا توجد أوقات متاحة في تاريخ {date}.",
                ctx_patch={},
                version=ctx.version,
            )

        human_times = [s.get("time") for s in slots if s.get("time")]
        text = ", ".join(human_times)

        if ctx.appointment_date and ctx.appointment_date != date:
            text = "تم تحديث التاريخ. يرجى اختيار الوقت والطبيب من جديد. " + text

        patch = {
            "appointment_date": date,
            "available_times": slots,
            "next_booking_step": BOOKING_STEP_TRANSITIONS[BookingStep.SELECT_DATE][0],
        }

        return ToolResult(public_text=text, ctx_patch=patch, private_data=slots, version=ctx.version)
    except BookingFlowError as e:
        return ToolResult(
            public_text=f"عذراً، حدث خطأ في فحص الأوقات: {str(e)}",
            ctx_patch={},
            version=ctx.version,
        )


@function_tool
async def suggest_employees(
    wrapper: RunContextWrapper[BookingContext], time: str
) -> ToolResult:
    """Get available employees and pricing for a specific date/time.

    Args:
        time: The time to check for available employees (HH:MM format)
    """
    ctx = wrapper.context

    error = _validate_step(ctx, BookingStep.SELECT_TIME)
    if error:
        return ToolResult(public_text=error, ctx_patch={}, version=ctx.version)

    if not ctx.selected_services_pm_si:
        return ToolResult(public_text="عذراً، يجب اختيار الخدمات أولاً.", ctx_patch={}, version=ctx.version)

    if not ctx.appointment_date:
        return ToolResult(public_text="عذراً، يجب تحديد التاريخ أولاً.", ctx_patch={}, version=ctx.version)

    if not time:
        return ToolResult(public_text="عذراً، يجب تحديد الوقت أولاً.", ctx_patch={}, version=ctx.version)

    parsed_time = booking_tool.parse_natural_time(time)
    time = parsed_time or time

    if not ctx.available_times:
        return ToolResult(public_text="عذراً، يجب فحص الأوقات المتاحة أولاً.", ctx_patch={}, version=ctx.version)

    times = {t.get("time") for t in ctx.available_times if t.get("time")}
    if time not in times:
        human_times = ", ".join(sorted(times))
        return ToolResult(
            public_text=f"عذراً، الوقت {time} غير متاح. الأوقات المتاحة: {human_times}",
            ctx_patch={},
            version=ctx.version,
        )

    gender = ctx.gender or "male"

    try:
        employees, checkout_summary = await booking_tool.get_available_employees(
            ctx.appointment_date, time, ctx.selected_services_pm_si, gender
        )
    except BookingFlowError as e:
        return ToolResult(
            public_text=f"عذراً، حدث خطأ في جلب الأطباء: {str(e)}",
            ctx_patch={},
            version=ctx.version,
        )

    if not employees:
        alternatives = ", ".join(sorted(times))
        return ToolResult(
            public_text=f"عذراً، لا يوجد أطباء متاحون في {ctx.appointment_date} الساعة {time}. الأوقات المتاحة الأخرى: {alternatives}",
            ctx_patch={},
            version=ctx.version,
        )

    patch = {
        "appointment_time": time,
        "offered_employees": employees,
        "checkout_summary": checkout_summary,
        "next_booking_step": BOOKING_STEP_TRANSITIONS[BookingStep.SELECT_TIME][0],
    }

    message_data = {"employees": employees, "checkout_summary": checkout_summary}
    if ctx.appointment_time and ctx.appointment_time != time:
        prefix = "تم تحديث الوقت. يرجى اختيار الطبيب من جديد. "
    else:
        prefix = ""

    message = prefix + json.dumps(message_data, ensure_ascii=False)

    return ToolResult(
        public_text=message,
        ctx_patch=patch,
        private_data=message_data,
        version=ctx.version,
    )


@function_tool
async def create_booking(
    wrapper: RunContextWrapper[BookingContext], employee_pm_si: str
) -> ToolResult:
    """Create the final booking with all selected details.

    Args:
        employee_pm_si: The employee token to book with
    """
    ctx = wrapper.context

    error = _validate_step(ctx, BookingStep.SELECT_EMPLOYEE)
    if error:
        return ToolResult(public_text=error, ctx_patch={}, version=ctx.version)

    if not ctx.selected_services_pm_si:
        return ToolResult(public_text="عذراً، يجب اختيار الخدمات أولاً.", ctx_patch={}, version=ctx.version)

    if not ctx.appointment_date:
        return ToolResult(public_text="عذراً، يجب تحديد التاريخ أولاً.", ctx_patch={}, version=ctx.version)

    if not ctx.appointment_time:
        return ToolResult(public_text="عذراً، يجب تحديد الوقت أولاً.", ctx_patch={}, version=ctx.version)

    if not employee_pm_si:
        return ToolResult(public_text="عذراً، يجب اختيار الطبيب أولاً.", ctx_patch={}, version=ctx.version)

    employee = next(
        (emp for emp in (ctx.offered_employees or []) if emp.get("pm_si") == employee_pm_si),
        None,
    )
    patch = {
        "employee_pm_si": employee_pm_si,
        "employee_name": employee.get("name") if employee else None,
    }

    gender = ctx.gender or "male"

    # Re-check that the chosen slot is still available
    try:
        current_emps, _ = await booking_tool.get_available_employees(
            ctx.appointment_date,
            ctx.appointment_time,
            ctx.selected_services_pm_si,
            gender,
        )
        if not any(emp.get("pm_si") == employee_pm_si for emp in current_emps):
            slots = await booking_tool.get_available_times(
                ctx.appointment_date, ctx.selected_services_pm_si, gender
            )
            human_times = [s.get("time") for s in slots if s.get("time")]
            patch.update(
                {
                    "appointment_time": None,
                    "offered_employees": None,
                    "checkout_summary": None,
                    "available_times": slots,
                    "next_booking_step": BookingStep.SELECT_TIME,
                }
            )
            return ToolResult(
                public_text=
                "عذراً، تم حجز هذا الوقت بالفعل. الأوقات المتاحة الأخرى: "
                + ", ".join(human_times),
                ctx_patch=patch,
                private_data={"available_times": slots},
                version=ctx.version,
            )
    except BookingFlowError:
        # If availability check fails, proceed to booking attempt
        pass

    if ctx.patient_data:
        customer_info = {"customer_type": "exists", "customer_search": ctx.user_phone}
    else:
        if not ctx.user_name or not ctx.user_phone:
            return ToolResult(
                public_text="عذراً، نحتاج معلوماتك الشخصية لإكمال الحجز. ما اسمك ورقم هاتفك؟",
                ctx_patch=patch,
                version=ctx.version,
            )

        customer_info = {
            "customer_type": "new",
            "customer_name": ctx.user_name,
            "customer_phone": ctx.user_phone,
            "customer_gender": normalize_gender(ctx.customer_gender or gender),
        }

    chat_id = getattr(ctx, "chat_id", "")
    idempotency_key = (
        f"{chat_id}-{ctx.appointment_date}-{ctx.appointment_time}-"
        f"{employee_pm_si}-{hash(tuple(ctx.selected_services_pm_si))}"
    )

    try:
        result = await booking_tool.create_booking(
            ctx.appointment_date,
            ctx.appointment_time,
            employee_pm_si,
            ctx.selected_services_pm_si,
            customer_info,
            gender,
            idempotency_key=idempotency_key,
        )

        if result.get("result"):
            patch.update(
                {
                    "booking_confirmed": True,
                    "booking_in_progress": False,
                    "next_booking_step": BOOKING_STEP_TRANSITIONS[BookingStep.SELECT_EMPLOYEE][0],
                }
            )

        return ToolResult(
            public_text=json.dumps(result, ensure_ascii=False),
            ctx_patch=patch,
            private_data=result,
            version=ctx.version,
        )

    except BookingFlowError as e:
        try:
            slots = await booking_tool.get_available_times(
                ctx.appointment_date, ctx.selected_services_pm_si, gender
            )
            human_times = [s.get("time") for s in slots if s.get("time")]
            patch.update(
                {
                    "appointment_time": None,
                    "offered_employees": None,
                    "checkout_summary": None,
                    "available_times": slots,
                    "next_booking_step": BookingStep.SELECT_TIME,
                }
            )
            return ToolResult(
                public_text=
                f"عذراً، لم يعد الوقت {ctx.appointment_time} متاحاً. الأوقات المتاحة الأخرى: "
                + ", ".join(human_times),
                ctx_patch=patch,
                private_data={"available_times": slots},
                version=ctx.version,
            )
        except BookingFlowError:
            return ToolResult(
                public_text=f"عذراً، حدث خطأ في إنشاء الحجز: {str(e)}",
                ctx_patch=patch,
                version=ctx.version,
            )


@function_tool
async def reset_booking(wrapper: RunContextWrapper[BookingContext]) -> ToolResult:
    """Reset the booking process and start over."""
    ctx = wrapper.context
    patch = {
        "selected_services_pm_si": None,
        "selected_services_data": None,
        "appointment_date": None,
        "appointment_time": None,
        "total_price": None,
        "employee_pm_si": None,
        "employee_name": None,
        "booking_confirmed": False,
        "booking_in_progress": False,
        "next_booking_step": None,
        "pending_questions": None,
    }

    return ToolResult(
        public_text="تم إعادة تعيين عملية الحجز. يمكنك البدء من جديد! 😊",
        ctx_patch=patch,
        version=ctx.version,
    )


@function_tool
async def revert_to_step(
    wrapper: RunContextWrapper[BookingContext],
    step: Literal[
        "select_service",
        "select_date",
        "select_time",
        "select_employee",
    ],
) -> ToolResult:
    """Revert the booking flow to a previous ``step`` and invalidate downstream selections."""

    ctx = wrapper.context
    controller = StepController(ctx)
    start_version = ctx.version
    step_enum = BookingStep(step)
    controller.invalidate_downstream_fields(step_enum, expected_version=ctx.version)
    fields = StepController._DOWNSTREAM_FIELDS.get(step_enum, [])
    patch: Dict[str, Optional[str | List[str] | float | bool]] = {}
    if fields:
        primary = fields[0]
        patch[primary] = getattr(controller.ctx, primary)
    controller.revert_to(start_version)

    msg_map = {
        BookingStep.SELECT_SERVICE: "تم الرجوع إلى خطوة اختيار الخدمة. يرجى إعادة اختيار الخدمة، التاريخ، الوقت والطبيب.",
        BookingStep.SELECT_DATE: "تم الرجوع إلى خطوة اختيار التاريخ. يرجى إعادة اختيار التاريخ، الوقت والطبيب.",
        BookingStep.SELECT_TIME: "تم الرجوع إلى خطوة اختيار الوقت. يرجى إعادة اختيار الوقت والطبيب.",
        BookingStep.SELECT_EMPLOYEE: "تم الرجوع إلى خطوة اختيار الطبيب. يرجى إعادة اختيار الطبيب.",
    }

    return ToolResult(
        public_text=msg_map.get(step_enum, ""),
        ctx_patch=patch,
        version=ctx.version,
    )


@function_tool
async def update_booking_context(
    wrapper: RunContextWrapper[BookingContext], updates: BookingContextUpdate
) -> ToolResult:
    """Update fields in the booking context.

    Args:
        updates: Fields to update. All attributes are optional and correspond to
            those on :class:`BookingContext`:

            * ``selected_services_pm_si`` (``List[str]``): service tokens to
              reserve. Example: ``["svc123", "svc456"]``.
            * ``appointment_date`` (``str``): date in ``YYYY-MM-DD`` format.
            * ``appointment_time`` (``str``): time in ``HH:MM`` 24-hour format.
            * ``employee_pm_si`` (``str``): token of the chosen employee.
            * ``employee_name`` (``str``): human-readable employee name.
            * ``gender`` (``str``): ``"male"`` or ``"female"``.
            * ``next_booking_step`` (``BookingStep``): upcoming workflow step.

    Examples:
        >>> await update_booking_context(wrapper, BookingContextUpdate(
        ...     selected_services_pm_si=["svc123", "svc456"],
        ... ))
        >>> await update_booking_context(wrapper, BookingContextUpdate(
        ...     employee_pm_si="emp789", employee_name="Dr. Noor",
        ... ))
        >>> await update_booking_context(wrapper, BookingContextUpdate(
        ...     appointment_date="2024-06-01", appointment_time="14:30",
        ... ))
    """
    ctx = wrapper.context

    updates_dict = updates.model_dump(exclude_none=True)
    # ``next_booking_step`` is managed automatically by :class:`StepController`.
    # If provided, ignore it rather than returning an error so callers can send
    # payloads without needing to filter the field themselves.
    updates_dict.pop("next_booking_step", None)

    if not updates_dict:
        return ToolResult(
            public_text="لم يتم تقديم أي تحديثات.", ctx_patch={}, version=ctx.version
        )

    messages: list[str] = []
    controller = StepController(ctx)
    start_version = ctx.version
    msg_map = {
        BookingStep.SELECT_SERVICE: (
            "تم تحديث الخدمات. تم مسح الأوقات المتاحة، الأطباء المقترحين، وملخص الحجز. "
            "يرجى اختيار التاريخ، الوقت، والطبيب من جديد."
        ),
        BookingStep.SELECT_DATE: (
            "تم تحديث التاريخ. تم مسح الأوقات المتاحة، الأطباء المقترحين، وملخص الحجز. "
            "يرجى اختيار الوقت والطبيب من جديد."
        ),
        BookingStep.SELECT_TIME: (
            "تم تحديث الوقت. تم مسح الأطباء المقترحين وملخص الحجز. يرجى اختيار الطبيب من جديد."
        ),
    }
    for field in ["selected_services_pm_si", "appointment_date", "appointment_time"]:
        if field in updates_dict and getattr(ctx, field) != updates_dict[field]:
            step = StepController._FIELD_TO_STEP[field]
            if step in msg_map:
                controller.invalidate_downstream_fields(
                    step, expected_version=ctx.version
                )
                messages.append(msg_map[step])
                controller.revert_to(start_version)

    text = "تم تحديث الحقول: " + ", ".join(updates_dict.keys())
    if messages:
        text += ". " + " ".join(messages)

    return ToolResult(public_text=text, ctx_patch=updates_dict, version=ctx.version)


__all__ = [
    "suggest_services",
    "check_availability",
    "suggest_employees",
    "create_booking",
    "reset_booking",
    "revert_to_step",
    "update_booking_context",
]
