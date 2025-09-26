"""
FastAPI application factory and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from .middleware import SecurityHeaders, LoggingMiddleware
from .webhooks import WhatsAppWebhook
from .handlers import HealthHandler


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Noor AI Agent",
        description="WhatsApp AI assistant for Best Clinic 24",
        version="4.0.0",
        debug=settings.debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(SecurityHeaders)
    app.add_middleware(LoggingMiddleware)

    # Initialize handlers
    health_handler = HealthHandler()
    whatsapp_webhook = WhatsAppWebhook()

    # Register routes
    app.include_router(health_handler.router, prefix="/health", tags=["health"])
    app.include_router(whatsapp_webhook.router, prefix="/webhook", tags=["webhooks"])

    return app
