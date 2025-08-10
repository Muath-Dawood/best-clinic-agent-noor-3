from fastapi import FastAPI

# middleware
from src.app.middleware import SecurityHeaders

# routers
from src.app.health import router as health_router
from src.app.whatsapp_webhook import router as wa_router

app = FastAPI(title="Noor Agent")

# ✅ enable security headers
app.add_middleware(SecurityHeaders)

# ✅ mount routers
app.include_router(health_router)  # GET /health
app.include_router(wa_router, prefix="/webhook")  # POST /webhook/wa

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.app.main:app", host="0.0.0.0", port=8001, reload=True)
