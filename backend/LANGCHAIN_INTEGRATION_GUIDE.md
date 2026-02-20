"""
LangChain Integration
Comprehensive guide to using LangChain with OpenAI, Gemini, and other providers
"""

# LangChain Integration Guide

## Quick Start

### 1. Installation

Dependencies have been added to `requirements.txt`. Install them:

```bash
pip install -r requirements.txt
```

This includes:
- `langchain==0.1.20` - Core LangChain framework
- `langchain-core==0.1.50` - Core interfaces and types
- `langchain-openai==0.1.20` - OpenAI integration
- `langchain-google-genai==1.0.8` - Google Gemini integration
- `langchain-community==0.1.20` - Community tools and utilities
- `langgraph==0.1.0` - For orchestrating multi-step workflows

### 2. Configuration

Create a `.env` file with your API keys (copy from `.env.example`):

```bash
# For OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o

# For Gemini
# LLM_PROVIDER=gemini
# GOOGLE_API_KEY=AIzaSy...your-key-here
# GEMINI_MODEL=gemini-2.0-flash
```

### 3. Basic Usage

```python
from config.llm_config import get_llm
from langchain_core.messages import HumanMessage

# Get configured LLM (automatically uses .env settings)
llm = get_llm()

# Create and invoke
message = HumanMessage(content="What is voice authentication?")
response = llm.invoke([message])
print(response.content)
```

---

## Provider Guides

### OpenAI Integration

**File:** `config/openai_config.py`

```python
from config.openai_config import (
    OpenAIConfig,
    get_openai_llm,
    get_openai_voice_agent_llm
)

# Default OpenAI LLM
llm = get_openai_llm()

# Optimized for voice agent (low temperature, deterministic)
llm = get_openai_voice_agent_llm()

# Custom configuration
config = OpenAIConfig(
    model="gpt-4o",
    temperature=0.1,
    max_tokens=2048
)
llm = config.get_llm()

# Cost-optimized selection
llm = OpenAIConfig.get_cost_optimized_llm(max_budget_per_call=0.01)
```

**Available Models:**
- `gpt-4o` (latest, recommended) - $15/$60 per 1M tokens
- `gpt-4-turbo` - $10/$30 per 1M tokens
- `gpt-4` - $30/$60 per 1M tokens
- `gpt-3.5-turbo` - $0.50/$1.50 per 1M tokens

### Google Gemini Integration

**File:** `config/gemini_config.py`

```python
from config.gemini_config import (
    GeminiConfig,
    get_gemini_llm,
    get_gemini_voice_agent_llm,
    get_gemini_conversation_llm
)

# Default Gemini LLM
llm = get_gemini_llm()

# Optimized for voice agent
llm = get_gemini_voice_agent_llm()

# Optimized for conversation
llm = get_gemini_conversation_llm()

# Long context (1M tokens)
llm = GeminiConfig.create_for_long_context()

# Custom configuration
config = GeminiConfig(
    model="gemini-2.0-flash",
    temperature=0.1,
    max_tokens=2048
)
llm = config.get_llm()
```

**Available Models:**
- `gemini-2.0-flash` (latest, recommended) - $0.075/$0.30 per 1M tokens
- `gemini-1.5-pro` (most capable) - $3.50/$10.50 per 1M tokens
- `gemini-1.5-flash` (balanced) - $0.075/$0.30 per 1M tokens

**Gemini Advantages:**
- 1M token context window (vs 128K for GPT-4)
- Faster inference with Flash models
- Lower cost for long contexts
- Excellent for document processing

---

## Core Configuration

**File:** `config/llm_config.py`

Central configuration that auto-detects and switches between providers:

```python
from config.llm_config import (
    get_llm_config,
    get_llm,
    LLMConfig
)

# Get current configuration
config = get_llm_config()
print(f"Provider: {config.provider}")
print(f"Model: {config.model}")
print(f"Temperature: {config.temperature}")

# Get LLM instance
llm = get_llm()

# Create with specific provider
llm = LLMConfig.create_llm(provider="gemini")

# Reset configuration (useful for testing)
from config.llm_config import reset_llm_config
reset_llm_config()
```

---

## Common Use Cases

### 1. Voice Agent Query Compilation

Convert user speech to MongoDB queries:

```python
from config.openai_config import get_openai_voice_agent_llm
from langchain_core.messages import SystemMessage, HumanMessage

llm = get_openai_voice_agent_llm()

messages = [
    SystemMessage(content="""You are a MongoDB query compiler.
Convert user requests to MongoDB JSON queries.
Always include user_id for security."""),
    HumanMessage(content="Show my recent enrollments")
]

response = llm.invoke(messages)
print(response.content)  # Returns MongoDB query JSON
```

### 2. Conversational AI

Build natural conversations with users:

```python
from config.gemini_config import get_gemini_conversation_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

llm = get_gemini_conversation_llm()

conversation = [
    SystemMessage(content="You are a voice auth support assistant."),
    HumanMessage(content="How do I enroll my voice?"),
    AIMessage(content="To enroll, upload a WAV file and say your phrase..."),
    HumanMessage(content="What if it fails?"),
]

response = llm.invoke(conversation)
print(response.content)
```

### 3. Prompt Templates

Reusable prompts with variable inputs:

```python
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from config.llm_config import get_llm

prompt = ChatPromptTemplate.from_template(
    "Analyze voice quality for user {user_id}. "
    "Sample rate: {sample_rate}Hz, Duration: {duration}s"
)

chain = prompt | get_llm()
result = chain.invoke({
    "user_id": "user_123",
    "sample_rate": 16000,
    "duration": 5
})
print(result.content)
```

### 4. Error Handling with Fallback

Graceful degradation to backup provider:

```python
from config.openai_config import OpenAIConfig
from config.gemini_config import GeminiConfig
import logging

logger = logging.getLogger(__name__)

def get_llm_with_fallback():
    """Get LLM with automatic fallback"""
    try:
        # Try primary provider
        llm = OpenAIConfig.create_for_voice_agent()
        logger.info("Using OpenAI")
        return llm
    except Exception as e:
        logger.error(f"OpenAI failed: {e}")
        try:
            # Fallback to Gemini
            llm = GeminiConfig.create_for_voice_agent()
            logger.info("Falling back to Gemini")
            return llm
        except Exception as e2:
            logger.error(f"Gemini also failed: {e2}")
            raise
```

---

## Integration with FastAPI

### Basic Integration

```python
from fastapi import FastAPI
from config.llm_config import get_llm
from langchain_core.messages import HumanMessage

app = FastAPI()

@app.post("/query")
async def process_query(user_input: str):
    """Process user query with LLM"""
    llm = get_llm()
    
    message = HumanMessage(content=user_input)
    response = llm.invoke([message])
    
    return {"response": response.content}
```

### With Streaming (for real-time responses)

```python
from fastapi.responses import StreamingResponse
from config.llm_config import get_llm

@app.post("/query-stream")
async def process_query_streaming(user_input: str):
    """Stream LLM response for real-time feedback"""
    llm = get_llm()
    
    async def generate():
        message = HumanMessage(content=user_input)
        # Note: Requires LLM with streaming support
        for chunk in llm.stream([message]):
            if hasattr(chunk, 'content'):
                yield chunk.content
    
    return StreamingResponse(generate(), media_type="text/plain")
```

### With WebSocket Integration

```python
from fastapi import WebSocket
from config.llm_config import get_llm

@app.websocket("/ws/conversation")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    llm = get_llm()
    
    conversation = []
    
    while True:
        data = await websocket.receive_text()
        
        # Add user message
        from langchain_core.messages import HumanMessage
        conversation.append(HumanMessage(content=data))
        
        # Get response
        response = llm.invoke(conversation)
        
        # Send response
        await websocket.send_text(response.content)
        
        # Add AI message to history
        from langchain_core.messages import AIMessage
        conversation.append(AIMessage(content=response.content))
```

---

## Running Examples

Run included integration examples:

```bash
# Run all examples
python langchain_integration_examples.py

# Run specific example
python langchain_integration_examples.py 1  # Example 1: Basic Usage
python langchain_integration_examples.py 5  # Example 5: Query Compilation
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| LLM_PROVIDER | openai | Primary provider (openai, gemini) |
| LLM_TEMPERATURE | 0.1 | Sampling temperature (0-2) |
| LLM_MAX_TOKENS | 4096 | Max output tokens |
| LLM_TOP_P | 0.95 | Nucleus sampling |
| OPENAI_API_KEY | - | OpenAI API key (required) |
| OPENAI_MODEL | gpt-4o | OpenAI model name |
| GOOGLE_API_KEY | - | Google API key (for Gemini) |
| GEMINI_MODEL | gemini-2.0-flash | Gemini model name |

---

## Troubleshooting

### "OPENAI_API_KEY not found"
```python
# Make sure .env is in backend/ directory with:
OPENAI_API_KEY=sk-your-key

# Or set directly in Python:
import os
os.environ["OPENAI_API_KEY"] = "sk-your-key"
```

### "GOOGLE_API_KEY not found"
```python
# Ensure .env has:
GOOGLE_API_KEY=AIzaSy...

# Get key from:
# https://makersuite.google.com/app/apikey
```

### Rate Limiting
```python
# Implement backoff for rate limits
import time
from langchain_core.messages import HumanMessage

for attempt in range(3):
    try:
        response = llm.invoke([HumanMessage(content="...")])
        break
    except Exception as e:
        if attempt < 2:
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
```

### Token Limit Exceeded

For OpenAI, reduce max_tokens:
```python
config = OpenAIConfig(max_tokens=2048)
```

For Gemini, use multi-request approach:
```python
config = GeminiConfig(model="gemini-1.5-pro")  # 1M context window
```

---

## Cost Optimization

### OpenAI
- Use `gpt-3.5-turbo` for simple tasks ($0.50/$1.50 per 1M)
- Use `gpt-4o` for complex queries ($15/$60 per 1M)
- Enable caching for repeated patterns

### Gemini
- Use `gemini-2.0-flash` for speed and cost ($0.075/$0.30)
- Use `gemini-1.5-pro` for complex reasoning ($3.50/$10.50)
- Leverage 1M token context for document batch processing

### General Tips
```python
# 1. Use low temperature for deterministic tasks
config = OpenAIConfig(temperature=0.1)

# 2. Set reasonable token limits
config = OpenAIConfig(max_tokens=1024)

# 3. Use cheaper models for routine tasks
llm = OpenAIConfig.get_cost_optimized_llm(max_budget_per_call=0.01)

# 4. Batch requests when possible
llm = OpenAIConfig.create_for_voice_agent()
responses = [llm.invoke([msg]) for msg in messages]
```

---

## Next Steps

1. **Test with your voice data**: Run examples with actual voice enrollment/verification queries
2. **Integrate with FastAPI**: Add LLM routes to main.py
3. **Add to WebSocket handlers**: Stream responses in real-time
4. **Monitor costs**: Track API usage in OpenAI/Gemini dashboards
5. **Optimize prompts**: Fine-tune system messages for your use cases

---

## Additional Resources

- [LangChain Documentation](https://python.langchain.com/docs/)
- [OpenAI API Docs](https://platform.openai.com/docs/)
- [Google Gemini API Docs](https://ai.google.dev/docs)
- [LangChain Community](https://github.com/langchain-ai/langchain)

---

## Support

For issues or questions:
1. Check `.env.example` for required configuration
2. Review `langchain_integration_examples.py` for usage patterns
3. Check error logs for API key or rate limit issues
4. Verify API keys haven't been revoked in provider dashboards
