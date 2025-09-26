"""
Main application entry point for Noor AI Agent.
"""

import uvicorn
from .api.app import create_app

# Create the FastAPI application
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "noor_ai_agent.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
