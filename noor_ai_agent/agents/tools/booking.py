"""
Booking tools for the Noor AI agent.
"""

from typing import List, Optional, Dict, Any
from agents import function_tool, RunContextWrapper

from ...core.models.booking import BookingContext, BookingContextUpdate
from ...core.enums import BookingStep, Gender
from ...core.exceptions import BookingFlowError
from ...services.booking import BookingService
from ...utils.validation import ValidationUtils
from .result import ToolResult


class BookingTools:
    """Collection of booking-related tools for the AI agent."""

    def __init__(self, booking_service: BookingService):
        self.booking_service = booking_service

    @function_tool
    async def suggest_services(self, wrapper: RunContextWrapper[BookingContext]) -> ToolResult:
        """Show available services based on the user's gender preference."""
        ctx = wrapper.context

        # Check if we're at the right step
        if ctx.next_booking_step not in (None, BookingStep.SELECT_SERVICE):
            return ToolResult(
                public_text="عذراً، لا يمكن عرض الخدمات في هذه المرحلة.",
                ctx_patch={},
                version=ctx.version,
            )

        gender = ctx.effective_gender()

        try:
            services = await self.booking_service.get_available_services(gender)
            if not services:
                return ToolResult(
                    public_text="عذراً، لا توجد خدمات متاحة لهذا القسم حالياً.",
                    ctx_patch={},
                    version=ctx.version,
                )

            # Format services for display
            service_text = self._format_services_list(services)

            # Update context
            patch = {
                "selected_services_data": services,
                "next_booking_step": BookingStep.SELECT_SERVICE,
            }

            return ToolResult(
                public_text=service_text,
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
        self,
        wrapper: RunContextWrapper[BookingContext],
        date: str
    ) -> ToolResult:
        """Get available times for a specific date."""
        ctx = wrapper.context

        # Validate step
        if ctx.next_booking_step not in (BookingStep.SELECT_DATE, BookingStep.SELECT_TIME, BookingStep.SELECT_EMPLOYEE):
            return ToolResult(
                public_text="عذراً، لا يمكن فحص المواعيد في هذه المرحلة.",
                ctx_patch={},
                version=ctx.version,
            )

        if not ctx.selected_services_pm_si:
            return ToolResult(
                public_text="عذراً، يجب اختيار الخدمات أولاً.",
                ctx_patch={},
                version=ctx.version,
            )

        if not date:
            return ToolResult(
                public_text="عذراً، يجب تحديد التاريخ أولاً.",
                ctx_patch={},
                version=ctx.version,
            )

        # Parse date
        parsed_date = self.booking_service.parse_natural_date(date, ctx.user_lang or "ar")
        if not parsed_date:
            return ToolResult(
                public_text="لو سمحت، أعطني تاريخاً محدداً (مثل 2025-08-21) أو يوم أسبوع واضح (مثل الاثنين القادم) لنكمل الحجز.",
                ctx_patch={},
                version=ctx.version,
            )

        try:
            slots = await self.booking_service.get_available_times(
                parsed_date,
                ctx.selected_services_pm_si,
                ctx.effective_gender()
            )

            if not slots:
                return ToolResult(
                    public_text=f"عذراً، لا توجد أوقات متاحة في تاريخ {parsed_date}.",
                    ctx_patch={"available_times": None},
                    version=ctx.version,
                )

            # Format times for display
            times_text = self._format_available_times(slots)

            # Update context
            patch = {
                "appointment_date": parsed_date,
                "available_times": slots,
                "next_booking_step": BookingStep.SELECT_TIME,
            }

            return ToolResult(
                public_text=times_text,
                ctx_patch=patch,
                private_data=slots,
                version=ctx.version,
            )
        except BookingFlowError as e:
            return ToolResult(
                public_text=f"عذراً، حدث خطأ في فحص الأوقات: {str(e)}",
                ctx_patch={},
                version=ctx.version,
            )

    @function_tool
    async def suggest_employees(
        self,
        wrapper: RunContextWrapper[BookingContext],
        time: str
    ) -> ToolResult:
        """Get available employees and pricing for a specific time."""
        ctx = wrapper.context

        # Validate step
        if ctx.next_booking_step not in (BookingStep.SELECT_TIME, BookingStep.SELECT_EMPLOYEE):
            return ToolResult(
                public_text="عذراً، لا يمكن عرض الأطباء في هذه المرحلة.",
                ctx_patch={},
                version=ctx.version,
            )

        if not ctx.selected_services_pm_si:
            return ToolResult(
                public_text="عذراً، يجب اختيار الخدمات أولاً.",
                ctx_patch={},
                version=ctx.version,
            )

        if not ctx.appointment_date:
            return ToolResult(
                public_text="عذراً، يجب تحديد التاريخ أولاً.",
                ctx_patch={},
                version=ctx.version,
            )

        if not time:
            return ToolResult(
                public_text="عذراً، يجب تحديد الوقت أولاً.",
                ctx_patch={},
                version=ctx.version,
            )

        # Parse time
        parsed_time = self.booking_service.parse_natural_time(time)
        time = parsed_time or time

        try:
            employees, checkout_summary = await self.booking_service.get_available_employees(
                ctx.appointment_date,
                time,
                ctx.selected_services_pm_si,
                ctx.effective_gender()
            )

            if not employees:
                return ToolResult(
                    public_text=f"عذراً، لا يوجد أطباء متاحون في {ctx.appointment_date} الساعة {time}.",
                    ctx_patch={},
                    version=ctx.version,
                )

            # Format employees for display
            employees_text = self._format_employees_list(employees, checkout_summary)

            # Update context
            patch = {
                "appointment_time": time,
                "offered_employees": employees,
                "checkout_summary": checkout_summary,
                "next_booking_step": BookingStep.SELECT_EMPLOYEE,
            }

            return ToolResult(
                public_text=employees_text,
                ctx_patch=patch,
                private_data={"employees": employees, "checkout": checkout_summary},
                version=ctx.version,
            )
        except BookingFlowError as e:
            return ToolResult(
                public_text=f"عذراً، حدث خطأ في جلب الأطباء: {str(e)}",
                ctx_patch={},
                version=ctx.version,
            )

    @function_tool
    async def create_booking(
        self,
        wrapper: RunContextWrapper[BookingContext],
        employee_pm_si: Optional[str] = None
    ) -> ToolResult:
        """Create the final booking with all selected details."""
        ctx = wrapper.context

        # Validate step
        if ctx.next_booking_step not in (BookingStep.SELECT_EMPLOYEE, None):
            return ToolResult(
                public_text="عذراً، لا يمكن تأكيد الحجز في هذه المرحلة.",
                ctx_patch={},
                version=ctx.version,
            )

        # Validate required fields
        validation_errors = self.booking_service.validate_booking_context(ctx)
        if validation_errors:
            return ToolResult(
                public_text="، ".join(validation_errors),
                ctx_patch={},
                version=ctx.version,
            )

        # Use provided employee or context employee
        target_emp = employee_pm_si or ctx.employee_pm_si
        if not target_emp:
            return ToolResult(
                public_text="رجاءً اختر الطبيب من الأسماء المعروضة قبل تأكيد الحجز.",
                ctx_patch={},
                version=ctx.version,
            )

        try:
            # Build idempotency key
            idempotency_key = self.booking_service.build_booking_idempotency_key(ctx)

            # Create booking
            result = await self.booking_service.create_booking(
                ctx.appointment_date,
                ctx.appointment_time,
                target_emp,
                ctx.selected_services_pm_si,
                ctx.customer_pm_si,
                ctx.effective_gender(),
                idempotency_key=idempotency_key,
            )

            if result.get("result"):
                # Booking successful
                patch = {
                    "booking_confirmed": True,
                    "booking_in_progress": False,
                }

                # Format success message
                success_text = self._format_booking_success(ctx)

                return ToolResult(
                    public_text=success_text,
                    ctx_patch=patch,
                    private_data=result,
                    version=ctx.version,
                )
            else:
                # Booking failed
                return ToolResult(
                    public_text="عذراً، لم نتمكن من تأكيد الحجز حالياً. جرب وقتاً مختلفاً أو تاريخاً آخر.",
                    ctx_patch={},
                    private_data=result,
                    version=ctx.version,
                )
        except BookingFlowError as e:
            return ToolResult(
                public_text=f"عذراً، حدث خطأ في تأكيد الحجز: {str(e)}",
                ctx_patch={},
                version=ctx.version,
            )

    @function_tool
    async def update_booking_context(
        self,
        wrapper: RunContextWrapper[BookingContext],
        updates: BookingContextUpdate
    ) -> ToolResult:
        """Update fields in the booking context."""
        ctx = wrapper.context

        # Validate and process updates
        processed_updates = self._process_context_updates(updates, ctx)

        if not processed_updates:
            return ToolResult(
                public_text="لم يتم تقديم أي تحديثات صالحة.",
                ctx_patch={},
                version=ctx.version,
            )

        # Apply updates
        for key, value in processed_updates.items():
            setattr(ctx, key, value)

        # Update version
        ctx.version += 1

        return ToolResult(
            public_text="تم تحديث المعلومات بنجاح.",
            ctx_patch=processed_updates,
            version=ctx.version,
        )

    def _format_services_list(self, services: List[Dict]) -> str:
        """Format services list for display."""
        if not services:
            return "لا توجد خدمات متاحة"

        lines = []
        for service in services:
            title = service.get("title", "خدمة")
            price = service.get("price", "0")
            duration = service.get("duration", "00:30")
            lines.append(f"• {title} - {price} ₪ ({duration})")

        return "\n".join(lines)

    def _format_available_times(self, slots: List[Dict]) -> str:
        """Format available times for display."""
        if not slots:
            return "لا توجد أوقات متاحة"

        times = [slot.get("time") for slot in slots if slot.get("time")]
        return "الأوقات المتاحة: " + ", ".join(times)

    def _format_employees_list(self, employees: List[Dict], checkout_summary: Dict) -> str:
        """Format employees list for display."""
        if not employees:
            return "لا يوجد أطباء متاحون"

        lines = []
        for emp in employees:
            name = emp.get("display") or emp.get("name") or "طبيب"
            lines.append(f"• {name}")

        return "\n".join(lines)

    def _format_booking_success(self, ctx: BookingContext) -> str:
        """Format booking success message."""
        subject_info = ctx.get_subject_info()
        who = subject_info["name"] if not ctx.booking_for_self else (ctx.user_name or "المراجع")

        return (
            f"✅ تم تأكيد حجز {who} "
            f"يوم {ctx.appointment_date} الساعة {ctx.appointment_time} "
            f"مع {ctx.employee_name or 'الطبيب المختار'}. أهلاً وسهلاً!"
        )

    def _process_context_updates(self, updates: BookingContextUpdate, ctx: BookingContext) -> Dict[str, Any]:
        """Process and validate context updates."""
        processed = {}

        # Process each field
        for field, value in updates.dict().items():
            if value is None or field == "next_booking_step":
                continue

            # Validate specific fields
            if field == "user_phone" and value:
                is_valid, error_msg = ValidationUtils.validate_palestinian_phone(value)
                if not is_valid:
                    continue  # Skip invalid phone numbers

            if field == "user_name" and value:
                is_valid, error_msg = ValidationUtils.validate_name(value)
                if not is_valid:
                    continue  # Skip invalid names

            processed[field] = value

        return processed
