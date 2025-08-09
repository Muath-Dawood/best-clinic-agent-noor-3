from fastapi import FastAPI
from .health import router as health_router
from .whatsapp_webhook import router as wa_router

app = FastAPI(title="Noor AI Agent 3")

app.include_router(health_router, prefix="/health")
app.include_router(wa_router, prefix="/webhook")
