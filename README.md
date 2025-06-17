# Multi-Agent Workflow System

A sophisticated stateless multi-agent system built with LangChain and monitored with Langfuse Cloud for production-ready AI workflows.

## Features

- 🤖 **Multi-Agent Architecture**: Orchestrated agent system with specialized tools
- 📊 **Cloud Monitoring**: Integrated with [Langfuse Cloud](https://langfuse.com) for comprehensive tracing and analytics
- 🔧 **Flexible Tools**: Extensible tool system for various operations
- 🚀 **Production Ready**: Containerized deployment with health checks and logging
- 🛡️ **Type Safety**: Full TypeScript-style validation with Pydantic
- 📈 **Stateless Design**: No local data persistence required
- ⚡ **Lightweight**: Minimal infrastructure dependencies

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │ Langfuse Cloud  │
│                 │────│   (External)    │
│ Multi-Agent     │    │                 │
│ System          │    │ Traces &        │
│ (Stateless)     │    │ Analytics       │
└─────────────────┘    └─────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- [Langfuse Cloud Account](https://cloud.langfuse.com) (free tier available)
- [Mistral API Key](https://console.mistral.ai/) (for LLM integration)

## Quick Start

### 1. Get Langfuse Cloud Credentials

1. Sign up at [Langfuse Cloud](https://cloud.langfuse.com)
2. Create a new project
3. Go to project settings to get your API keys:
   - `LANGFUSE_PUBLIC_KEY` (starts with `pk-lf-...`)
   - `LANGFUSE_SECRET_KEY` (starts with `sk-lf-...`)

### 2. Setup Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Update `.env` with your credentials:

```env
# Langfuse Cloud Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
# 🇪🇺 EU region
LANGFUSE_HOST=https://cloud.langfuse.com
# 🇺🇸 US region (uncomment if using US region)
# LANGFUSE_HOST=https://us.cloud.langfuse.com

# Mistral API Configuration
MISTRAL_API_KEY=your_mistral_api_key_here

# Application Configuration
LOG_LEVEL=INFO
```

### 3. Start the System

```bash
# Start the application
docker-compose up -d

# Check service health
curl http://localhost:8000/health
```

### 4. Test the Agent

```bash
# Example request
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Calculate 15 * 23 and explain the result",
    "session_id": "test-session"
  }'
```

## API Endpoints

### Health Check
```
GET /health
```
Returns system health status and metrics.

### Agent Information
```
GET /agent/info
```
Returns detailed information about the agent configuration.

### Invoke Agent
```
POST /invoke
```
Execute agent with user input.

**Request Body:**
```json
{
  "input": "Your question or task",
  "session_id": "optional-session-id",
  "metadata": {
    "optional": "metadata"
  }
}
```

**Response:**
```json
{
  "output": "Agent response",
  "session_id": "session-id",
  "request_id": "unique-request-id",
  "intermediate_steps": [...],
  "metadata": {...}
}
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Yes | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | Yes | - |
| `LANGFUSE_HOST` | Langfuse host URL | No | `https://cloud.langfuse.com` |
| `MISTRAL_API_KEY` | Mistral API key | Yes | - |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Configuration Files

- `settings/model_config.json`: LLM model configuration
- `settings/langfuse_config.json`: Langfuse client settings
- `prompts/main_orchestrator_system.md`: Main agent system prompt

## Available Tools

The system currently includes the following tools:

- **Math Operator**: Performs basic mathematical calculations
- **Extensible Framework**: Easy to add new tools via the `src/tools/operators/` directory

## Monitoring & Analytics

The system automatically sends traces to Langfuse Cloud for:

- 📊 **Request Tracking**: Every API call is traced
- 🔍 **Agent Debugging**: Step-by-step execution visibility  
- 💰 **Cost Monitoring**: Token usage and cost tracking
- 📈 **Performance Analytics**: Response times and success rates
- 🏷️ **Session Grouping**: Conversation-level insights

Access your traces at: [cloud.langfuse.com](https://cloud.langfuse.com)

## Development

### Local Development

```bash
# Install dependencies
cd src
pip install -r requirements.txt

# Run locally (requires environment setup)
python main.py
```

### Adding New Tools

1. Create tool in `src/tools/operators/`
2. Register in `src/tools/factory.py`
3. Update agent configuration if needed

### Extending Agents

The system supports multiple agent types. See `src/agent_factory.py` for examples.

## Deployment

### Production Considerations

1. **Security**: Use secrets management for API keys
2. **Scaling**: The stateless design makes horizontal scaling easy
3. **Monitoring**: Set up additional monitoring with health check endpoints
4. **Networking**: Consider using a reverse proxy for production

### Docker Compose Override

For production, create `docker-compose.override.yml`:

```yaml
services:
  app:
    environment:
      - LOG_LEVEL=WARNING
    restart: unless-stopped
```

## Troubleshooting

### Common Issues

1. **Langfuse Connection Failed**
   - Verify API keys are correct
   - Check internet connectivity
   - Ensure correct region (EU/US)

2. **Agent Tools Not Loading**
   - Check tool dependencies
   - Verify tool registration in factory

3. **Mistral API Issues**
   - Verify API key is valid
   - Check API rate limits
   - Ensure network connectivity

### Logs

```bash
# View application logs
docker-compose logs app

# Follow logs in real-time
docker-compose logs -f app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- 📚 [Langfuse Documentation](https://langfuse.com/docs)
- 🐛 [Report Issues](https://github.com/yourusername/multi-agent-workflow-test/issues)
- 💬 [Discussion Forum](https://github.com/yourusername/multi-agent-workflow-test/discussions) 