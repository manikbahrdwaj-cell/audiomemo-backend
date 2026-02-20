"""
LangChain Integration Quick Start
Get started in 5 minutes
"""

# QUICK START GUIDE

## 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

**Installed:** langchain 1.2.10, langchain-openai, langchain-google-genai, langgraph

---

## 2. Set Up Environment Variables

**Create `.env` file in `backend/` directory:**

### Option A: Use OpenAI (GPT-4)
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
```

### Option B: Use Google Gemini (Recommended - Cheaper)
```bash
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
```

**See `.env.example` for all options**

---

## 3. Basic Usage

### Minimal Example
```python
from config.llm_config import get_llm
from langchain_core.messages import HumanMessage

llm = get_llm()
response = llm.invoke([HumanMessage(content="Hello!")])
print(response.content)
```

### Voice Agent Query Example
```python
from config.llm_config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

llm = get_llm()

messages = [
    SystemMessage(content="Convert to MongoDB query"),
    HumanMessage(content="Show my recent enrollments")
]

response = llm.invoke(messages)
print(response.content)  # Returns JSON query
```

---

## 4. Provider-Specific Usage

### Use OpenAI Directly
```python
from config.openai_config import OpenAIConfig

config = OpenAIConfig(model="gpt-4o")
llm = config.get_llm()
```

### Use Gemini Directly
```python
from config.gemini_config import GeminiConfig

config = GeminiConfig(model="gemini-2.0-flash")
llm = config.get_llm()
```

---

## 5. Run Examples

```bash
# Run all examples
python langchain_integration_examples.py

# Run specific example
python langchain_integration_examples.py 1  # Basic usage
python langchain_integration_examples.py 5  # Query compilation
```

---

## 6. Integration with FastAPI

```python
from fastapi import FastAPI
from config.llm_config import get_llm
from langchain_core.messages import HumanMessage

app = FastAPI()

@app.post("/voice-query")
async def process_query(text: str):
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=text)])
    return {"response": response.content}
```

---

## 7. Troubleshooting

| Problem | Solution |
|---------|----------|
| "API key not found" | Ensure `.env` file exists in `backend/` with correct key |
| "No module named langchain" | Run `pip install -r requirements.txt` |
| Rate limiting | Add delay between requests: `import time; time.sleep(1)` |
| Token limit exceeded | Reduce `LLM_MAX_TOKENS` in `.env` |

---

## 8. Cost Optimization

**OpenAI:**
- Use `gpt-3.5-turbo` for cost savings
- Use `gpt-4o` for complex tasks

**Gemini:**
- Use `gemini-2.0-flash` (cheapest, fastest)
- Use `gemini-1.5-pro` for long documents (1M tokens)

---

## File Structure

```
backend/
├── requirements.txt                    # Dependencies (updated with LangChain)
├── .env                               # Your config (create from .env.example)
├── .env.example                       # Template with all options
├── config/
│   ├── __init__.py                   # Package exports
│   ├── llm_config.py                 # Central config (generic)
│   ├── openai_config.py              # OpenAI specific
│   └── gemini_config.py              # Google Gemini specific
├── langchain_integration_examples.py  # 10 working examples
└── LANGCHAIN_INTEGRATION_GUIDE.md    # Full documentation
```

---

## Next Steps

1. Copy `.env.example` to `.env` and add your API key
2. Run `python langchain_integration_examples.py` to test
3. Integrate `from config.llm_config import get_llm` into your FastAPI routes
4. Add WebSocket support for streaming responses
5. Monitor costs in OpenAI/Gemini dashboards

---

## Key Classes & Functions

| Import | Purpose |
|--------|---------|
| `get_llm()` | Get configured LLM (auto-detects provider) |
| `get_llm_config()` | Get config object (provider, model, etc) |
| `OpenAIConfig` | OpenAI-specific configuration & utilities |
| `GeminiConfig` | Gemini-specific configuration & utilities |
| `ChatOpenAI`, `ChatGoogleGenerativeAI` | LLM instances from langchain packages |

---

## Example: Conversation History

```python
from config.llm_config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

llm = get_llm()

conversation = [
    SystemMessage(content="You are a helpful assistant"),
    HumanMessage(content="What is voice auth?"),
    AIMessage(content="Voice authentication is..."),
    HumanMessage(content="How does enrollment work?"),
]

response = llm.invoke(conversation)
print(response.content)
```

---

## Documentation

- Full guide: `LANGCHAIN_INTEGRATION_GUIDE.md`
- Examples: `langchain_integration_examples.py`
- Config: `config/llm_config.py`, `config/openai_config.py`, `config/gemini_config.py`

---

**You're ready to use LangChain!** Start with example 1 to test your setup.
