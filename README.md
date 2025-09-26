# Noor AI Agent 4.0

A comprehensive WhatsApp AI assistant for Best Clinic 24, built with modern Python architecture and best practices.

## Features

- **WhatsApp Integration**: Seamless WhatsApp webhook handling with Green API
- **Appointment Booking**: Complete booking flow with service selection, date/time picking, and doctor selection
- **Patient Management**: Integration with clinic database for existing patients
- **Multi-language Support**: Arabic and English conversation support
- **Memory Management**: Conversation summaries and context persistence
- **Knowledge Base**: Vector store integration for clinic information retrieval

## Architecture

The application follows a clean, modular architecture:

```
noor_ai_agent/
├── core/                    # Core business logic
│   ├── models/             # Data models
│   ├── enums/              # Enumerations
│   └── exceptions/         # Custom exceptions
├── services/               # Business logic services
│   ├── booking/            # Appointment booking
│   ├── patient/            # Patient management
│   ├── memory/             # Conversation memory
│   └── external/           # External API integration
├── api/                    # API layer
│   ├── webhooks/           # Webhook handlers
│   ├── middleware/         # Custom middleware
│   └── handlers/           # Request handlers
├── agents/                 # AI agents
│   ├── noor/              # Main conversational agent
│   ├── kb/                # Knowledge base agent
│   └── tools/             # Agent tools
├── utils/                  # Utility functions
├── config/                 # Configuration management
└── tests/                  # Test suite
```

## Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- WhatsApp Green API credentials
- Best Clinic API access

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd noor-ai-agent-4
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements_new.txt
```

4. Create environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application:
```bash
python -m noor_ai_agent
```

### Configuration

Create a `.env` file with the following variables:

```env
# Application
DEBUG=false
LOG_LEVEL=INFO

# OpenAI
OPENAI_API_KEY=your_openai_api_key
VECTOR_STORE_ID_KB=your_vector_store_id

# WhatsApp Green API
WA_GREEN_ID_INSTANCE=your_green_id
WA_GREEN_API_TOKEN=your_green_token
WA_VERIFY_SECRET=your_webhook_secret

# Best Clinic API
BEST_CLINIC_API_BASE=https://www.bestclinic24.net
BEST_CLINIC_API_TOKEN=your_api_token
PATIENT_LOOKUP_TIMEOUT=10.0

# Database
STATE_DB_PATH=state.db
SESSIONS_DB_PATH=noor_sessions.db

# Timezone
TIMEZONE=Asia/Hebron
```

## API Endpoints

- `GET /health` - Health check
- `POST /webhook/wa` - WhatsApp webhook

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

The codebase follows these principles:

- **Type Hints**: Full type annotation support
- **Pydantic Models**: Data validation and serialization
- **Async/Await**: Non-blocking I/O operations
- **Error Handling**: Comprehensive exception handling
- **Logging**: Structured logging throughout
- **Documentation**: Comprehensive docstrings

### Adding New Features

1. **Models**: Add new data models in `core/models/`
2. **Services**: Implement business logic in `services/`
3. **API**: Add new endpoints in `api/handlers/`
4. **Agents**: Extend AI capabilities in `agents/`

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements_new.txt .
RUN pip install -r requirements_new.txt

COPY . .
CMD ["python", "-m", "noor_ai_agent"]
```

### Environment Variables

Ensure all required environment variables are set in your deployment environment.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is proprietary software for Best Clinic 24.

## Support

For support and questions, contact the development team.
