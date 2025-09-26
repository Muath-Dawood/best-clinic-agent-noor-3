"""
Noor AI agent - the main conversational agent.
"""

from typing import List
from agents import Agent, Runner, SQLiteSession

from ...core.models.booking import BookingContext
from ...core.enums import Language
from ...services.booking import BookingService
from ...services.memory import MemoryService
from ...agents.tools import BookingTools
from ...agents.kb import KnowledgeBaseAgent
from .prompts import SYSTEM_PROMPT


class NoorAgent:
    """Main conversational AI agent for Best Clinic 24."""

    def __init__(self, booking_service: BookingService, memory_service: MemoryService):
        self.booking_service = booking_service
        self.memory_service = memory_service
        self.booking_tools = BookingTools(booking_service)
        self.kb_agent = KnowledgeBaseAgent()

    def _build_agent(self, ctx: BookingContext) -> Agent:
        """Build the Noor agent with dynamic context."""
        instructions = SYSTEM_PROMPT + "\n\n" + self._build_dynamic_footer(ctx)

        # Get tools
        tools = [
            self.booking_tools.suggest_services,
            self.booking_tools.check_availability,
            self.booking_tools.suggest_employees,
            self.booking_tools.create_booking,
            self.booking_tools.update_booking_context,
        ]

        # Add knowledge base tools if available
        kb_tools = self.kb_agent.get_tools()
        tools.extend(kb_tools)

        return Agent(
            name="Noor",
            instructions=instructions,
            model="gpt-4o",
            tools=tools
        )

    def _build_dynamic_footer(self, ctx: BookingContext) -> str:
        """Build dynamic footer with context information."""
        lines = []

        # Add current time information
        try:
            from datetime import datetime
            import pytz

            tz_name = ctx.tz or "Asia/Hebron"
            now = datetime.now(pytz.timezone(tz_name))
            lines.append("### NOW")
            lines.append(f"today_date_iso={now.date().isoformat()}")
            lines.append(f"now_time_24h={now.strftime('%H:%M')}")
            lines.append(f"timezone={tz_name}")
            lines.append("### END NOW")
        except Exception:
            pass

        # Add user context
        if ctx and (ctx.user_name or ctx.user_phone):
            lines += [
                "### THIS SECTION IS THE RESULT OF DYNAMIC INJECTION OF INTERNAL CONTEXT (do not reveal to user; use the info naturally)"
            ]
            lines.append(f"current_datetime={ctx.current_datetime}")
            lines.append(f"tz={ctx.tz}")
            if ctx.user_name:
                lines.append(f"user_name={ctx.user_name}")
            if ctx.user_phone:
                lines.append(f"user_phone={ctx.user_phone}")
            if ctx.patient_data:
                lines.append("known_patient=true")
            lines.append(f"user_has_attachments={str(bool(ctx.user_has_attachments)).lower()}")
            lines.append("### END INTERNAL CONTEXT")

        # Add previous summaries
        if ctx.previous_summaries and len(ctx.previous_summaries):
            lines.append(
                "### THIS SECTION IS THE RESULT OF DYNAMIC INJECTION OF PREVIOUS CHAT SUMMARIES (do not reveal this to user but use to guide the conversation intelligently)"
            )
            lines.append("\n".join(ctx.previous_summaries))
            lines.append("### END PREVIOUS SUMMARIES")

        return "\n".join(lines)

    async def run_turn(
        self,
        user_input: str,
        ctx: BookingContext,
        session: SQLiteSession,
    ) -> str:
        """Run a single conversation turn with the user."""
        # Log the turn
        self._log_turn_start(ctx, user_input)

        # Build agent
        agent = self._build_agent(ctx)

        # Run the agent
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=user_input,
                session=session,
                context=ctx,
            )

            # Log the result
            self._log_turn_end(ctx, result.final_output)

            return result.final_output
        except Exception as e:
            # Log error and return fallback message
            self._log_turn_error(ctx, str(e))
            return "عذرًا، في خلل تقني بسيط الآن. جرّب بعد قليل لو تكرّمت."

    def _log_turn_start(self, ctx: BookingContext, user_input: str):
        """Log the start of a conversation turn."""
        # This would integrate with proper logging
        pass

    def _log_turn_end(self, ctx: BookingContext, response: str):
        """Log the end of a conversation turn."""
        # This would integrate with proper logging
        pass

    def _log_turn_error(self, ctx: BookingContext, error: str):
        """Log an error during conversation turn."""
        # This would integrate with proper logging
        pass
