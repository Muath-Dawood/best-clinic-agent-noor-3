"""
Main entry point for Noor AI Agent.
"""

from noor_ai_agent.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
