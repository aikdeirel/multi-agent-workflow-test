# Multi-Agent Orchestration System

**⚠️ EXPERIMENTAL PROJECT - FOR LEARNING & TESTING PURPOSES ONLY**

This is a personal experiment and educational project for exploring multi-agent systems, LangChain, and AI workflow patterns. This project is **NOT intended for production use** and is purely for experimentation, testing, and self-education purposes.

A sophisticated multi-agent orchestration system that demonstrates true delegation patterns between specialized AI agents, built with LangChain and monitored with Langfuse Cloud.

## Multi-Agent Architecture Overview

This system implements a **true multi-agent delegation pattern** where:

1. **Main Orchestrator Agent** - Receives user requests and delegates to specialized operators
2. **Weather Operator Agent** - Specialized agent for weather-related tasks with weather tools
3. **Math Operator Agent** - Specialized agent for mathematical calculations with math tools

### How the Multi-Agent System Works

Here's a real example of how the system handles complex requests:

**User**: *"What's the weather in Berlin and Munich? Compare the results and tell me which is better."*

**System Flow**:
1. **Orchestrator**: "I need weather for Berlin and Munich but cannot get weather myself. Let me ask the weather operator for Berlin first."
   - Delegates to Weather Operator: "Get weather for Berlin"

2. **Weather Operator**: "You want weather for Berlin? I'll use my weather tools."
   - Uses `get_current_weather` tool → Gets Berlin weather data
   - Returns: "Here's the weather for Berlin: 15°C, cloudy, 60% humidity..."

3. **Orchestrator**: "Great! Now I need Munich weather too. Let me ask the weather operator for Munich."
   - Delegates to Weather Operator: "Get weather for Munich"

4. **Weather Operator**: "You want weather for Munich? I'll use my weather tools."
   - Uses `get_current_weather` tool → Gets Munich weather data  
   - Returns: "Here's the weather for Munich: 18°C, sunny, 45% humidity..."

5. **Orchestrator**: "Perfect! Now I have both weather reports. I can compare them myself."
   - Analyzes both results internally
   - Returns: "Based on the weather data, Munich has better weather today with warmer temperatures (18°C vs 15°C), sunny conditions vs cloudy, and lower humidity."

### Key Features

- 🤖 **True Agent Delegation**: Orchestrator delegates to specialized agents, never performs tasks directly
- 🔧 **Specialized Tools**: Each operator has domain-specific tools (weather APIs, math calculators)
- 📊 **Cloud Monitoring**: Integrated with [Langfuse Cloud](https://langfuse.com) for comprehensive tracing
- 🧪 **Extensible**: Easy to add new operator agents and tools
- ⚡ **Sequential Processing**: Handles complex multi-step requests through proper delegation
- 🛡️ **Type Safety**: Full validation with Pydantic
- 📈 **Stateless Design**: No local data persistence required

## Architecture Diagram

```
┌─────────────────────┐    ┌─────────────────────┐
│   Main Orchestrator │    │    Langfuse Cloud   │
│       Agent         │────│   (Monitoring)      │
│                     │    │                     │
└──────────┬──────────┘    └─────────────────────┘
           │
           │ delegates to
           │
┌──────────▼──────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Weather Operator   │    │   Math Operator     │    │  [Future Operator]  │
│      Agent          │    │      Agent          │    │      Agent          │
│                     │    │                     │    │                     │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │  Weather Tools  │ │    │ │   Math Tools    │ │    │ │  Custom Tools   │ │
│ │ • Current       │ │    │ │ • Calculator    │ │    │ │ • Database      │ │
│ │ • Forecast      │ │    │ │ • Expression    │ │    │ │ • Files         │ │
│ │ • Geocoding     │ │    │ │   Evaluator     │ │    │ │ • API Calls     │ │
│ └─────────────────┘ │    │ └─────────────────┘ │    │ │ • ...           │ │
└─────────────────────┘    └─────────────────────┘    │ └─────────────────┘ │
                                                      └─────────────────────┘
                                                            ⬆ Easily
                                                          Extensible
```

## Available Agents & Tools

### Main Orchestrator Agent
- **Role**: Central coordinator and task delegator
- **Capabilities**: Understands user intent, delegates to specialists, combines results
- **Never**: Performs calculations or weather lookups directly

### Weather Operator Agent  
- **Role**: Weather specialist with weather tools
- **Tools**:
  - `get_current_weather` - Real-time weather data
  - `get_weather_forecast` - Multi-day forecasts
  - `weather_help` - Weather information guidance
- **Data Source**: Open-Meteo API (free, no API key required)

### Math Operator Agent
- **Role**: Mathematics specialist with calculation tools  
- **Tools**:
  - `calculate` - Safe mathematical expression evaluation
  - `math_help` - Mathematical guidance
- **Features**: Supports arithmetic, functions, order of operations

## Prerequisites

- Docker and Docker Compose
- [Langfuse Cloud Account](https://cloud.langfuse.com) (free tier available)
- [Mistral API Key](https://console.mistral.ai/) (for LLM integration)

**🤖 LLM Support**: This project currently supports **Mistral LLM API only**. Other LLM providers are not supported at this time.

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
# Mistral model to use (default: mistral-medium-latest - recommended)
MISTRAL_MODEL=mistral-medium-latest

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

### 4. Test the Multi-Agent System

```bash
# Simple weather request
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What is the weather in London?",
    "session_id": "test-session"
  }'

# Multi-step weather comparison
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Compare weather between Paris and Rome, which is better?",
    "session_id": "test-session"
  }'

# Mathematical calculation
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Calculate 15 * 23 + 47 and explain the steps",
    "session_id": "test-session"
  }'

# Complex multi-agent request
curl -X POST "http://localhost:8000/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Get weather for Berlin and calculate 25 * 4, then tell me both results",
    "session_id": "test-session"
  }'
```

## API Endpoints

### Health Check
```
GET /health
```
Returns system health status and agent information.

### Agent Information
```
GET /agent/info
```
Returns detailed information about the orchestrator and available operators.

### Invoke Multi-Agent System
```
POST /invoke
```
Execute orchestrator with user input - it will delegate to appropriate specialist agents.

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
  "output": "Orchestrator's final response after agent delegation",
  "session_id": "session-id",
  "request_id": "unique-request-id",
  "intermediate_steps": ["Delegation steps and operator responses"],
  "metadata": {"agent_info": "orchestrator details"}
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
| `MISTRAL_MODEL` | Mistral model name | No | `mistral-medium-latest` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Configuration Files

- `settings/model_config.json`: LLM model configuration (Mistral)
- `settings/langfuse_config.json`: Langfuse client settings
- `prompts/main_orchestrator_system.md`: Main orchestrator system prompt
- `prompts/weather_operator_system.md`: Weather specialist system prompt  
- `prompts/math_operator_system.md`: Math specialist system prompt


## Monitoring & Analytics

The system automatically sends traces to Langfuse Cloud for:

- 📊 **Multi-Agent Tracing**: See delegation flow between orchestrator and operators
- 🔍 **Agent Debugging**: Step-by-step execution visibility for each agent
- 📈 **Performance Analytics**: Response times for delegations
- 🏷️ **Session Grouping**: Multi-turn conversation insights
- 🛠️ **Tool Usage**: Track which tools each operator uses

Access your traces at: [cloud.langfuse.com](https://cloud.langfuse.com)

## Development

### Adding New Operator Agents

1. Create new operator agent in `src/operators/`
2. Create tools in `src/tools/operators/`
3. Add system prompt in `prompts/`
4. Add import and register in `src/agent_factory.py`:
   ```python
   from operators.your_new_operator_agent import your_operator
   
   # Then add to the operators list in get_operator_agents()
   operators = [weather_operator, math_operator, your_operator]
   ```

### Extending the System

The architecture supports easy extension:
- **New Agents**: Add specialists for other domains (database, file system, etc.)
- **New Tools**: Extend existing operators with additional capabilities
- **Custom Prompts**: Modify agent behavior via prompt engineering

## Important Notes

### Experimental Nature

This project is designed for:
- 🧪 **Learning**: Understanding multi-agent delegation patterns
- 🔬 **Experimentation**: Testing AI orchestration concepts
- 📚 **Education**: Personal skill development in LangChain and multi-agent systems
- 🛠️ **Prototyping**: Rapid testing of agent coordination patterns

### Not Suitable For:
- ❌ Production deployments
- ❌ Commercial applications  
- ❌ Mission-critical systems
- ❌ Handling sensitive data

## Troubleshooting

### Common Issues

1. **Langfuse Connection Failed**
   - Verify API keys are correct
   - Check internet connectivity
   - Ensure correct region (EU/US)

2. **Agent Delegation Not Working**
   - Check operator agent registration
   - Verify tool imports
   - Review system prompts

3. **Weather Data Unavailable**
   - Open-Meteo API requires internet access
   - Location geocoding may fail for invalid locations

4. **Math Calculations Failing**
   - Check expression syntax
   - Verify calculator tool is loaded

### Logs

```bash
# View application logs with agent delegation traces
docker-compose logs app

# Follow logs in real-time to see agent interactions
docker-compose logs -f app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with various multi-agent scenarios
5. Submit a pull request

## License

This project is provided as-is for educational and experimental purposes.

## Support

- 📚 [Langfuse Documentation](https://langfuse.com/docs)
- 🐛 [Report Issues](https://github.com/yourusername/multi-agent-workflow-test/issues)