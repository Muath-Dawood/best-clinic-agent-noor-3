"""
WhatsApp webhook handler.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Response, status
from agents import SQLiteSession

from ...core.models.booking import BookingContext
from ...core.models.user import User
from ...core.enums import Gender, CustomerType, Language
from ...services.booking import BookingService
from ...services.patient import PatientService
from ...services.memory import MemoryService, StateManager
from ...services.external import ExternalAPIService
from ...utils.text import WhatsAppTextExtractor, TextProcessor
from ...utils.phone import PhoneNumberParser
from ...utils.date import DateParser
from ...config import get_settings


class WhatsAppWebhook:
    """Handler for WhatsApp webhook events."""

    def __init__(self):
        self.settings = get_settings()
        self.router = APIRouter()

        # Initialize services
        self.external_api = ExternalAPIService()
        self.state_manager = StateManager()
        self.memory_service = MemoryService()
        self.patient_service = PatientService(self.external_api)
        self.booking_service = BookingService(self.external_api, None)  # Will be injected

        # Initialize utilities
        self.text_extractor = WhatsAppTextExtractor()
        self.text_processor = TextProcessor()
        self.phone_parser = PhoneNumberParser()
        self.date_parser = DateParser()

        # Simple in-memory deduplication
        self._last_msgid: Dict[str, str] = {}

        self._setup_routes()

    def _setup_routes(self):
        """Setup WhatsApp webhook routes."""

        @self.router.post("/wa")
        async def receive_whatsapp_message(request: Request):
            """Handle incoming WhatsApp messages."""
            try:
                body = await request.json()
            except Exception:
                return Response(status_code=status.HTTP_400_BAD_REQUEST)

            # Extract text and check for attachments
            extraction_result = self.text_extractor.extract_text_from_wa(body)
            text_in = extraction_result.text
            had_attach = extraction_result.had_attachments

            msg_id = body.get("idMessage")
            sender_id = body.get("senderData", {}).get("chatId")

            # Log incoming message
            self._log_incoming_message(sender_id, msg_id)

            # Verify signature if configured
            if self.settings.wa_verify_secret:
                if not self._verify_signature(request):
                    self._log_verification_failed(sender_id, msg_id)
                    return Response(status_code=status.HTTP_401_UNAUTHORIZED)

            # Check for duplicate messages
            if sender_id and msg_id:
                if self._is_duplicate_message(sender_id, msg_id):
                    return {"ok": True, "dedupe": True}
                self._last_msgid[sender_id] = msg_id

            # Handle attachment-only messages
            if had_attach and not text_in:
                await self._send_whatsapp_message(
                    sender_id,
                    "استقبلت ملف/صورة. رجاءً اكتب رسالتك نصّياً حتى أقدر أساعدك 🌟"
                )
                return {"ok": True}

            # Ignore empty messages
            if not text_in:
                return {"status": "ignored"}

            # Process the message
            await self._process_message(sender_id, text_in, body)

            return {"status": "ok"}

    def _log_incoming_message(self, sender_id: str, msg_id: str):
        """Log incoming WhatsApp message."""
        # This would integrate with proper logging
        pass

    def _log_verification_failed(self, sender_id: str, msg_id: str):
        """Log verification failure."""
        # This would integrate with proper logging
        pass

    def _verify_signature(self, request: Request) -> bool:
        """Verify webhook signature."""
        # Implement signature verification logic
        return True

    def _is_duplicate_message(self, sender_id: str, msg_id: str) -> bool:
        """Check if message is a duplicate."""
        last = self._last_msgid.get(sender_id)
        return last == msg_id

    async def _process_message(self, sender_id: str, text: str, body: Dict[str, Any]):
        """Process incoming WhatsApp message."""
        # Load or create state
        state = await self.state_manager.get_state(sender_id)
        if state:
            ctx, session = state
            is_new_session = False
        else:
            ctx = BookingContext()
            session = SQLiteSession(sender_id, self.settings.sessions_db_path)
            is_new_session = True

        # Create user from WhatsApp data
        user = User.from_whatsapp_data(sender_id, body.get("senderData", {}))

        # Enrich context with user data
        await self._enrich_context(ctx, user, body)

        # Look up patient data
        await self._lookup_patient_data(ctx, sender_id)

        # Prefetch recent summaries for new sessions
        if is_new_session:
            await self._prefetch_summaries(ctx, sender_id)

        # Process with AI agent (this would integrate with the agent system)
        try:
            reply = await self._process_with_agent(text, ctx, session)
        except Exception as e:
            # Log error and send fallback message
            reply = "عذرًا، في خلل تقني بسيط الآن. جرّب بعد قليل لو تكرّمت."

        # Send reply
        await self._send_reply(sender_id, reply)

        # Save state
        await self.state_manager.save_state(sender_id, ctx, session)

    async def _enrich_context(self, ctx: BookingContext, user: User, body: Dict[str, Any]):
        """Enrich booking context with user data."""
        # Set user phone
        if not ctx.user_phone:
            try:
                ctx.user_phone = self.phone_parser.parse_whatsapp_to_local_palestinian_number(user.chat_id)
            except Exception:
                pass

        # Set user name
        if not ctx.user_name:
            ctx.user_name = user.profile.name

        # Set language
        if not ctx.user_lang:
            ctx.user_lang = user.profile.language.value

        # Set timezone
        ctx.tz = user.profile.timezone

    async def _lookup_patient_data(self, ctx: BookingContext, sender_id: str):
        """Look up patient data if not already present."""
        if ctx.patient_data is None:
            try:
                patient = await self.patient_service.lookup_patient_by_whatsapp_id(sender_id)
                if patient:
                    ctx.patient_data = patient.details.dict()
                    ctx.customer_pm_si = patient.details.pm_si
                    ctx.customer_type = CustomerType.EXISTING

                    # Prefer DB name over WhatsApp display name
                    db_name = patient.details.name
                    if db_name and db_name.strip():
                        ctx.user_name = db_name.strip()
                else:
                    ctx.customer_type = CustomerType.NEW
            except Exception:
                # Log error but don't crash
                ctx.customer_type = CustomerType.NEW

    async def _prefetch_summaries(self, ctx: BookingContext, sender_id: str):
        """Prefetch recent conversation summaries for new sessions."""
        try:
            summaries = await self.memory_service.fetch_recent_summaries(
                sender_id,
                ctx.user_phone
            )
            ctx.previous_summaries = summaries
        except Exception:
            # Log error but don't crash
            pass

    async def _process_with_agent(self, text: str, ctx: BookingContext, session: SQLiteSession) -> str:
        """Process message with AI agent."""
        # This would integrate with the actual AI agent system
        # For now, return a simple response
        return f"تم استلام رسالتك: {text}"

    async def _send_reply(self, sender_id: str, reply: str):
        """Send reply message to WhatsApp."""
        # Split message if too long
        chunks = self.text_processor.split_text_for_whatsapp(
            reply,
            self.settings.wa_max_message_length
        )

        for chunk in chunks:
            await self._send_whatsapp_message(sender_id, chunk)

    async def _send_whatsapp_message(self, chat_id: str, message: str):
        """Send message via WhatsApp API."""
        if not self.settings.wa_green_id_instance or not self.settings.wa_green_api_token:
            return

        success = await self.external_api.send_whatsapp_message(chat_id, message)
        if not success:
            # Log error
            pass
