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


"""
Booking Agent Tool - provides functional tools for Noor to handle appointment booking.
Uses the correct @function_tool pattern from Agents SDK.
"""

from typing import List, Dict, Optional
from agents import Agent, function_tool, RunContextWrapper

from src.tools.booking_tool import booking_tool, BookingFlowError
from src.data.services import get_services_by_gender, get_service_summary
from src.app.context_models import BookingContext


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

        return get_service_summary(services)
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

        # Format dates nicely
        formatted_dates = []
        for date in dates[:5]:  # Show max 5 dates
            try:
                from datetime import datetime

                dt = datetime.strptime(date, "%Y-%m-%d")
                formatted_dates.append(
                    dt.strftime("%A %d %B" if "ar" in gender else "%A %B %d")
                )
            except:
                formatted_dates.append(date)

        return f"المواعيد المتاحة:\n" + "\n".join(
            [f"• {date}" for date in formatted_dates]
        )
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

        # Format times nicely
        formatted_times = []
        for time in times[:8]:  # Show max 8 times
            try:
                from datetime import datetime

                dt = datetime.strptime(time, "%H:%M")
                formatted_times.append(
                    dt.strftime("%I:%M %p" if "en" in gender else "%H:%M")
                )
            except:
                formatted_times.append(time)

        return f"الأوقات المتاحة في {date}:\n" + "\n".join(
            [f"• {time}" for time in formatted_times]
        )
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

    gender = ctx.gender or "male"

    try:
        employees, pricing = await booking_tool.get_available_employees(
            ctx.appointment_date, time, ctx.selected_services_pm_si, gender
        )

        if not employees:
            return (
                f"عذراً، لا يوجد أطباء متاحون في {ctx.appointment_date} الساعة {time}."
            )

        # Update context with selected time
        ctx.appointment_time = time
        ctx.next_booking_step = "select_employee"
        ctx.total_price = float(pricing.get("full_total", 0))

        # Format employee list
        employee_list = []
        for emp in employees:
            status = (
                "متاح" if emp.get("employee_work_status") == "available" else "غير متاح"
            )
            employee_list.append(f"• {emp.get('name', 'غير محدد')} - {status}")

        # Add pricing info
        total = pricing.get("full_total", "غير محدد")

        response = f"الأطباء المتاحون:\n" + "\n".join(
            [f"• {emp.get('name', 'غير محدد')} - {status}" for emp in employees]
        )
        response += f"\n\n💰 السعر الإجمالي: {total} د.ك"

        return response
    except BookingFlowError as e:
        return f"عذراً، حدث خطأ في فحص الأطباء: {str(e)}"


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

            return f"✅ تم الحجز بنجاح!\n\n{result.get('message', '')}"
        else:
            return f"عذراً، فشل في إنشاء الحجز: {result.get('message', 'خطأ غير معروف')}"

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


# The mini-agent that owns the booking tools (Noor won't see the complex API calls directly)
_booking_agent = Agent(
    name="BookingAgent",
    instructions=(
        "You are a booking assistant for Best Clinic 24. Your job is to help users book appointments "
        "by understanding their requests and using the available tools intelligently.\n\n"
        "RULES:\n"
        "- Always respond in the user's language (Arabic or English)\n"
        "- Be helpful and conversational, not robotic\n"
        "- When suggesting dates/times, offer 2-3 options if available\n"
        "- If only one option is available, explain why and suggest it\n"
        "- Always confirm the final booking details before proceeding\n"
        "- Handle errors gracefully and suggest alternatives\n"
        "- Never mention technical details like API calls or tokens\n\n"
        "AVAILABLE TOOLS:\n"
        "- suggest_services: Show available services for a gender\n"
        "- check_availability: Check available dates for selected services\n"
        "- suggest_times: Get available times for a specific date\n"
        "- suggest_employees: Get available employees and pricing\n"
        "- create_booking: Finalize the booking\n"
        "- reset_booking: Start over if user wants to change something\n\n"
        "RESPOND NATURALLY and helpfully. Don't be a robot!"
    ),
    tools=[
        suggest_services,
        check_availability,
        suggest_times,
        suggest_employees,
        create_booking,
        reset_booking,
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
