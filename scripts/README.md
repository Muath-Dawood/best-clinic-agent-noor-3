# Noor AI Agent - Scripts

This directory contains scripts to manage the Noor AI Agent server.

## Available Scripts

### `run_api.sh`
Main script to start the Noor AI Agent server with full configuration options.

**Usage:**
```bash
./scripts/run_api.sh [OPTIONS]
```

**Options:**
- `-h, --host HOST` - Host to bind to (default: 0.0.0.0)
- `-p, --port PORT` - Port to bind to (default: 8000)
- `-w, --workers WORKERS` - Number of worker processes (default: 1)
- `-r, --reload` - Enable auto-reload for development
- `-l, --log-level LEVEL` - Log level (default: info)
- `--help` - Show help message

**Environment Variables:**
- `HOST` - Host to bind to
- `PORT` - Port to bind to
- `WORKERS` - Number of worker processes
- `RELOAD` - Enable auto-reload (true/false)
- `LOG_LEVEL` - Log level

**Examples:**
```bash
# Run with defaults
./scripts/run_api.sh

# Custom host and port
./scripts/run_api.sh --host 127.0.0.1 --port 9000

# Development mode with auto-reload
./scripts/run_api.sh --reload

# Production mode with multiple workers
./scripts/run_api.sh --workers 4

# Debug logging
./scripts/run_api.sh --log-level debug
```

### `run_dev.sh`
Quick script to run the server in development mode with auto-reload and debug logging.

**Usage:**
```bash
./scripts/run_dev.sh
```

**Features:**
- Auto-reload enabled
- Debug logging
- Single worker process
- Host: 0.0.0.0, Port: 8000

### `run_prod.sh`
Script to run the server in production mode with multiple workers.

**Usage:**
```bash
./scripts/run_prod.sh
```

**Features:**
- Multiple workers (default: 4, configurable via WORKERS env var)
- Info level logging
- Optimized for production

### `stop_api.sh`
Script to stop the running Noor AI Agent server.

**Usage:**
```bash
./scripts/stop_api.sh
```

**Features:**
- Graceful shutdown
- Force kill if needed
- Process detection and cleanup

## Quick Start

### Development
```bash
# Start development server
./scripts/run_dev.sh

# Stop server
./scripts/stop_api.sh
```

### Production
```bash
# Start production server
./scripts/run_prod.sh

# Stop server
./scripts/stop_api.sh
```

### Custom Configuration
```bash
# Custom port and host
./scripts/run_api.sh --host 0.0.0.0 --port 8080

# Multiple workers with custom log level
./scripts/run_api.sh --workers 8 --log-level warning
```

## Server Endpoints

Once the server is running, you can access:

- **Health Check**: `http://localhost:8000/health/`
- **API Documentation**: `http://localhost:8000/docs`
- **WhatsApp Webhook**: `http://localhost:8000/webhook/wa`

## Troubleshooting

### Port Already in Use
If you get a "port already in use" error:
```bash
# Stop existing server
./scripts/stop_api.sh

# Or use a different port
./scripts/run_api.sh --port 8001
```

### Dependencies Missing
The script will automatically check and install dependencies if needed.

### Permission Denied
Make sure the scripts are executable:
```bash
chmod +x scripts/*.sh
```

## Environment Configuration

Make sure you have a `.env` file with your configuration:
```bash
# Copy example if needed
cp .env.example .env

# Edit with your values
nano .env
```

Required environment variables:
- `OPENAI_API_KEY` - Your OpenAI API key
- `BEST_CLINIC_API_TOKEN` - Best Clinic API token
- `WA_GREEN_API_TOKEN` - WhatsApp Green API token
- `WA_VERIFY_SECRET` - WhatsApp webhook verification secret
