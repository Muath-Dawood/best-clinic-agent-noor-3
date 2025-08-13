"""
Booking Agent Tool - provides functional tools for Noor to handle appointment booking.
Uses the correct @function_tool pattern from Agents SDK.
"""

from typing import List, Dict, Optional
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


# Predefined employees to avoid repeated API calls. These are lightweight
# placeholders containing only the fields required by the booking flow.
employee_list: List[Dict[str, str]] = [
    {"pm_si": "emp_ahmad", "name": "Dr. Ahmad"},
    {"pm_si": "emp_sara", "name": "Dr. Sara"},
]


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
    ctx: BookingContext, expected: Optional[BookingStep]
) -> Optional[str]:
    """Ensure the booking flow is in the expected step."""
    if ctx.next_booking_step != expected:
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
async def suggest_services(wrapper: RunContextWrapper[BookingContext]) -> str:
    """Show available services based on the user's gender preference."""
    ctx = wrapper.context

    error = _validate_step(ctx, None)
    if error:
        return error

    # Determine gender from context or default to male
    gender = ctx.gender or "male"

    try:
        services = get_services_by_gender(gender)
        if not services:
            return "عذراً، لا توجد خدمات متاحة لهذا القسم حالياً."

        # Update context with available services
        ctx.selected_services_data = services
        ctx.next_booking_step = BOOKING_STEP_TRANSITIONS[None][0]

        # Return raw services data without modification
        return json.dumps(services, ensure_ascii=False)
    except Exception as e:
        return f"عذراً، حدث خطأ في جلب الخدمات: {str(e)}"


@function_tool
async def check_availability(wrapper: RunContextWrapper[BookingContext]) -> str:
    """Check available dates for selected services."""
    ctx = wrapper.context

    error = _validate_step(ctx, BookingStep.SELECT_SERVICE)
    if error:
        return error

    if not ctx.selected_services_pm_si:
        return "عذراً، يجب اختيار الخدمات أولاً قبل فحص التوفر."

    gender = ctx.gender or "male"

    try:
        dates = await booking_tool.get_available_dates(
            ctx.selected_services_pm_si, gender
        )
        if not dates:
            return "عذراً، لا توجد مواعيد متاحة للخدمات المختارة حالياً."

        # Update context with available dates
        ctx.next_booking_step = BOOKING_STEP_TRANSITIONS[BookingStep.SELECT_SERVICE][0]

        # Return raw dates exactly as received
        return json.dumps(dates, ensure_ascii=False)
    except BookingFlowError as e:
        return f"عذراً، حدث خطأ في فحص التوفر: {str(e)}"


@function_tool
async def suggest_times(wrapper: RunContextWrapper[BookingContext], date: str) -> str:
    """Get available times for a specific date.

    Args:
        date: The date to check for available times (YYYY-MM-DD format)
    """
    ctx = wrapper.context

    error = _validate_step(ctx, BookingStep.SELECT_DATE)
    if error:
        return error

    if not ctx.selected_services_pm_si:
        return "عذراً، يجب اختيار الخدمات أولاً."

    if not date:
        return "عذراً، يجب تحديد التاريخ أولاً."

    # Normalize natural language dates like "غداً" or "next Sunday"
    parsed_date = booking_tool.parse_natural_date(date, ctx.user_lang or "ar")
    date = parsed_date or date

    gender = ctx.gender or "male"

    try:
        times = await booking_tool.get_available_times(
            date, ctx.selected_services_pm_si, gender
        )
        if not times:
            return f"عذراً، لا توجد أوقات متاحة في تاريخ {date}."

        # Update context with selected date
        ctx.appointment_date = date
        ctx.next_booking_step = BOOKING_STEP_TRANSITIONS[BookingStep.SELECT_DATE][0]

        # Return raw times exactly as received
        return json.dumps(times, ensure_ascii=False)
    except BookingFlowError as e:
        return f"عذراً، حدث خطأ في فحص الأوقات: {str(e)}"


@function_tool
async def suggest_employees(
    wrapper: RunContextWrapper[BookingContext], time: str
) -> str:
    """Get available employees and pricing for a specific date/time.

    Args:
        time: The time to check for available employees (HH:MM format)
    """
    ctx = wrapper.context

    error = _validate_step(ctx, BookingStep.SELECT_TIME)
    if error:
        return error

    if not ctx.selected_services_pm_si:
        return "عذراً، يجب اختيار الخدمات أولاً."

    if not ctx.appointment_date:
        return "عذراً، يجب تحديد التاريخ أولاً."

    if not time:
        return "عذراً، يجب تحديد الوقت أولاً."

    # Normalize stored date and provided time if given in natural language
    parsed_date = booking_tool.parse_natural_date(
        ctx.appointment_date, ctx.user_lang or "ar"
    )
    ctx.appointment_date = parsed_date or ctx.appointment_date

    parsed_time = booking_tool.parse_natural_time(time)
    time = parsed_time or time

    # Use the pre-built employee_list and locally calculate pricing
    employees = employee_list
    if not employees:
        return f"عذراً، لا يوجد أطباء متاحون في {ctx.appointment_date} الساعة {time}."

    pricing_total = booking_tool.calculate_total_price(
        ctx.selected_services_pm_si or []
    )
    pricing = {"full_total": pricing_total}

    # Update context with selected time and pricing
    ctx.appointment_time = time
    ctx.next_booking_step = BOOKING_STEP_TRANSITIONS[BookingStep.SELECT_TIME][0]
    ctx.total_price = float(pricing_total)

    # Return employees and pricing exactly as received
    return json.dumps({"employees": employees, "pricing": pricing}, ensure_ascii=False)


@function_tool
async def create_booking(
    wrapper: RunContextWrapper[BookingContext], employee_pm_si: str
) -> str:
    """Create the final booking with all selected details.

    Args:
        employee_pm_si: The employee token to book with
    """
    ctx = wrapper.context

    error = _validate_step(ctx, BookingStep.SELECT_EMPLOYEE)
    if error:
        return error

    # Validate all required fields are present
    if not ctx.selected_services_pm_si:
        return "عذراً، يجب اختيار الخدمات أولاً."

    if not ctx.appointment_date:
        return "عذراً، يجب تحديد التاريخ أولاً."

    if not ctx.appointment_time:
        return "عذراً، يجب تحديد الوقت أولاً."

    if not employee_pm_si:
        return "عذراً، يجب اختيار الطبيب أولاً."

    # Persist chosen employee details using the pre-built list
    employee = next(
        (emp for emp in employee_list if emp.get("pm_si") == employee_pm_si),
        None,
    )
    ctx.employee_pm_si = employee_pm_si
    ctx.employee_name = employee.get("name") if employee else None

    gender = ctx.gender or "male"

    # Prepare customer info based on whether this is an existing or new patient
    if ctx.patient_data:
        # Existing patient
        customer_info = {"customer_type": "exists", "customer_search": ctx.user_phone}
    else:
        # New patient - need to collect required info
        if not ctx.user_name or not ctx.user_phone:
            return "عذراً، نحتاج معلوماتك الشخصية لإكمال الحجز. ما اسمك ورقم هاتفك؟"

        customer_info = {
            "customer_type": "new",
            "customer_name": ctx.user_name,
            "customer_phone": ctx.user_phone,
            "customer_gender": normalize_gender(ctx.customer_gender or gender),
        }

    try:
        result = await booking_tool.create_booking(
            ctx.appointment_date,
            ctx.appointment_time,
            employee_pm_si,
            ctx.selected_services_pm_si,
            customer_info,
            gender,
        )

        if result.get("result"):
            # Update context to mark booking as confirmed
            ctx.booking_confirmed = True
            ctx.booking_in_progress = False
            ctx.next_booking_step = BOOKING_STEP_TRANSITIONS[
                BookingStep.SELECT_EMPLOYEE
            ][0]

        # Return the full booking result without modification
        return json.dumps(result, ensure_ascii=False)

    except BookingFlowError as e:
        return f"عذراً، حدث خطأ في إنشاء الحجز: {str(e)}"


@function_tool
async def reset_booking(wrapper: RunContextWrapper[BookingContext]) -> str:
    """Reset the booking process and start over."""
    ctx = wrapper.context

    # Clear all booking-related fields
    ctx.selected_services_pm_si = None
    ctx.selected_services_data = None
    ctx.appointment_date = None
    ctx.appointment_time = None
    ctx.employee_pm_si = None
    ctx.employee_name = None
    ctx.total_price = None
    ctx.booking_confirmed = False
    ctx.booking_in_progress = False
    ctx.next_booking_step = None
    ctx.pending_questions = None

    return "تم إعادة تعيين عملية الحجز. يمكنك البدء من جديد! 😊"


@function_tool
async def update_booking_context(
    wrapper: RunContextWrapper[BookingContext], updates: BookingContextUpdate
) -> str:
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
    if not updates_dict:
        return "لم يتم تقديم أي تحديثات."

    for name, value in updates_dict.items():
        setattr(ctx, name, value)

    return "تم تحديث الحقول: " + ", ".join(updates_dict.keys())


__all__ = [
    "suggest_services",
    "check_availability",
    "suggest_times",
    "suggest_employees",
    "create_booking",
    "reset_booking",
    "update_booking_context",
]
