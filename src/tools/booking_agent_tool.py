"""
Booking Agent Tool - provides functional tools for Noor to handle appointment booking.
Uses the correct @function_tool pattern from Agents SDK.
"""

from typing import List, Dict, Optional, Any
import json
from agents import Agent, function_tool, RunContextWrapper

from src.tools.booking_tool import booking_tool, BookingFlowError
from src.data.services import get_services_by_gender
from src.app.context_models import BookingContext


# Predefined employees to avoid repeated API calls. These are lightweight
# placeholders containing only the fields required by the booking flow.
employee_list: List[Dict[str, str]] = [
    {"pm_si": "emp_ahmad", "name": "Dr. Ahmad"},
    {"pm_si": "emp_sara", "name": "Dr. Sara"},
]


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

    # Determine gender from context or default to male
    gender = ctx.gender or "male"

    try:
        services = get_services_by_gender(gender)
        if not services:
            return "عذراً، لا توجد خدمات متاحة لهذا القسم حالياً."

        # Update context with available services
        ctx.selected_services_data = services
        ctx.next_booking_step = "select_service"

        # Return raw services data without modification
        return json.dumps(services, ensure_ascii=False)
    except Exception as e:
        return f"عذراً، حدث خطأ في جلب الخدمات: {str(e)}"


@function_tool
async def check_availability(wrapper: RunContextWrapper[BookingContext]) -> str:
    """Check available dates for selected services."""
    ctx = wrapper.context

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
        ctx.next_booking_step = "select_date"

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

    if not ctx.selected_services_pm_si:
        return "عذراً، يجب اختيار الخدمات أولاً."

    if not date:
        return "عذراً، يجب تحديد التاريخ أولاً."

    gender = ctx.gender or "male"

    try:
        times = await booking_tool.get_available_times(
            date, ctx.selected_services_pm_si, gender
        )
        if not times:
            return f"عذراً، لا توجد أوقات متاحة في تاريخ {date}."

        # Update context with selected date
        ctx.appointment_date = date
        ctx.next_booking_step = "select_time"

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

    if not ctx.selected_services_pm_si:
        return "عذراً، يجب اختيار الخدمات أولاً."

    if not ctx.appointment_date:
        return "عذراً، يجب تحديد التاريخ أولاً."

    if not time:
        return "عذراً، يجب تحديد الوقت أولاً."

    # Use the pre-built employee_list and locally calculate pricing
    employees = employee_list
    if not employees:
        return (
            f"عذراً، لا يوجد أطباء متاحون في {ctx.appointment_date} الساعة {time}."
        )

    pricing_total = booking_tool.calculate_total_price(
        ctx.selected_services_pm_si or []
    )
    pricing = {"full_total": pricing_total}

    # Update context with selected time and pricing
    ctx.appointment_time = time
    ctx.next_booking_step = "select_employee"
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
            ctx.next_booking_step = None

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
    wrapper: RunContextWrapper[BookingContext], updates: Dict[str, Any]
) -> str:
    """Update fields in the booking context.

    Args:
        updates: Mapping of field names to new values. Keys should match
            attributes on :class:`BookingContext`. Common keys and formats:

            * ``selected_services_pm_si`` (``List[str]``): service tokens to
              reserve. Example: ``["svc123", "svc456"]``.
            * ``appointment_date`` (``str``): date in ``YYYY-MM-DD`` format.
            * ``appointment_time`` (``str``): time in ``HH:MM`` 24-hour format.
            * ``employee_pm_si`` (``str``): token of the chosen employee.
            * ``employee_name`` (``str``): human-readable employee name.
            * ``gender`` (``str``): ``"male"`` or ``"female"``.
            * ``next_booking_step`` (``str``): upcoming workflow step.

    Examples:
        >>> await update_booking_context(wrapper, {
        ...     "selected_services_pm_si": ["svc123", "svc456"],  # service_tokens
        ... })
        >>> await update_booking_context(wrapper, {
        ...     "employee_pm_si": "emp789",                        # employee_token
        ...     "employee_name": "Dr. Noor",
        ... })
        >>> await update_booking_context(wrapper, {
        ...     "appointment_date": "2024-06-01",
        ...     "appointment_time": "14:30",
        ... })
    """
    ctx = wrapper.context

    if not updates:
        return "لم يتم تقديم أي تحديثات."

    invalid_fields = [name for name in updates if not hasattr(ctx, name)]
    if invalid_fields:
        return (
            "عذراً، الحقول التالية غير معروفة: "
            + ", ".join(invalid_fields)
        )

    for name, value in updates.items():
        setattr(ctx, name, value)

    return "تم تحديث الحقول: " + ", ".join(updates.keys())


# The mini-agent that owns the booking tools (Noor won't see the complex API calls directly)
_booking_agent = Agent(
    name="BookingAgent",
    instructions=(
        "You are a booking assistant for Best Clinic 24. Help users book appointments by "
        "understanding their requests and using the tools.\n\n"
        "RULES:\n"
        "- Converse in the user's language (Arabic or English).\n"
        "- When you call a tool, return its output verbatim, including IDs or tokens. Do not translate, "
        "  summarize, or drop fields.\n"
        "- Outside of raw tool output, stay warm, helpful, and conversational.\n"
        "- When suggesting dates or times, offer 2-3 options if available; if only one exists, explain why.\n"
        "- Confirm all booking details before creating a booking.\n"
        "- Handle errors gracefully and suggest alternatives.\n"
        "- Avoid commentary about APIs or tools—just show the raw output when relevant.\n\n"
        "AVAILABLE TOOLS:\n"
        "- suggest_services: Show available services for a gender\n"
        "- check_availability: Check available dates for selected services\n"
        "- suggest_times: Get available times for a specific date\n"
        "- suggest_employees: Get available employees and pricing\n"
        "- create_booking: Finalize the booking\n"
        "- reset_booking: Start over if user wants to change something\n"
        "- update_booking_context: Modify booking details directly\n\n"
        "RESPOND NATURALLY and helpfully. Don't be a robot!"
    ),
    tools=[
        suggest_services,
        check_availability,
        suggest_times,
        suggest_employees,
        create_booking,
        reset_booking,
        update_booking_context,
    ],
    model="gpt-4o-mini",
)


def booking_tool_for_noor():
    """Return the tool object to plug into Noor.tools."""
    return [
        _booking_agent.as_tool(
            tool_name="handle_booking",
            tool_description=(
                "Handle appointment booking for Best Clinic 24. Use this when users want to book "
                "appointments, check availability, or discuss services. The tool can: show available "
                "services, check dates/times, suggest employees, and create bookings. Always respond "
                "naturally in the user's language."
            ),
        )
    ]
