# Noor AI Agent 3

Customer-facing WhatsApp agent for Best Clinic 24, built with OpenAI Agents SDK.

## Quick start
1) Create `.env` from `.env.example`
2) `pip install -r requirements.txt`
3) Run API: `uvicorn src.app.main:app --reload`

## Date parsing
Natural language dates are supported via `BookingTool.parse_natural_date`. If an
input resolves to a past date, the function returns the next occurrence for
weekday names or `None` when no future date is sensible (e.g., "yesterday").

