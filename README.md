# Noor AI Agent 3

Customer-facing WhatsApp agent for Best Clinic 24, built with OpenAI Agents SDK.

## Quick start
1) Create `.env` from `.env.example`
2) `pip install -r requirements.txt`
3) Run API: `uvicorn src.app.main:app --reload`

## Webhook security
Incoming WhatsApp callbacks must include a secret token:

1. Set `WA_WEBHOOK_TOKEN` in your environment.
2. Configure your WhatsApp provider to send the header `X-WA-TOKEN` with this value.

Requests missing or with an invalid token are logged and rejected with `401 Unauthorized`.

