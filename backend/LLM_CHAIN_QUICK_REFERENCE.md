# LLM Chain Builder - Quick Reference Card

## ⚡ 30-Second Start

```python
from llm_chain_builder import VoiceVerifiedLLMChain
import asyncio

chain = VoiceVerifiedLLMChain()

# Single message
result = await chain.process_user_message(
    phone_number="+1-555-0123",
    user_message="Hello!",
    verification_score=0.95
)
print(result['assistant_response'])
```

---

## 🔑 Key Classes & Methods

### VoiceVerifiedLLMChain

```python
# Initialize
chain = VoiceVerifiedLLMChain()
chain = VoiceVerifiedLLMChain(llm=custom_llm)

# Single message
await chain.process_user_message(
    phone_number: str,
    user_message: str,
    verification_score: float,
    session_id: Optional[str] = None
) -> Dict

# Multi-turn
await chain.process_multi_turn_conversation(
    phone_number: str,
    messages: List[str],
    verification_score: float
) -> Dict

# Advanced
chain.create_chain(config) -> Runnable
chain.create_system_prompt(config) -> str
```

---

## 📋 Common Patterns

### Pattern 1: REST API
```python
@app.post("/chat")
async def chat(phone: str, msg: str, score: float):
    return await chain.process_user_message(
        phone_number=phone,
        user_message=msg,
        verification_score=score
    )
```

### Pattern 2: WebSocket
```python
@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()
    result = await chain.process_user_message(
        phone_number=data['phone'],
        user_message=data['message'],
        verification_score=data['score'],
        session_id=data.get('session_id')
    )
    await ws.send_json(result)
```

### Pattern 3: Multi-Turn
```python
result = await chain.process_multi_turn_conversation(
    phone_number="+1-555-0123",
    messages=["Hi", "What's your rate?", "Thanks"],
    verification_score=0.95
)
```

### Pattern 4: Custom LLM
```python
from config.openai_config import OpenAIConfig
llm = OpenAIConfig(model="gpt-4-turbo").get_llm()
chain = VoiceVerifiedLLMChain(llm=llm)
```

---

## 📊 Response Format

### Single Message Response
```python
{
    "success": True,
    "session_id": "lg_session_xxxxx",
    "phone_number": "+1-555-0123",
    "user_message": "Hello!",
    "assistant_response": "Hello! How can I help?",
    "verification_score": 0.95,
    "timestamp": "2026-02-23T12:25:00.000Z"
}
```

### Multi-Turn Response
```python
{
    "success": True,
    "session_id": "lg_session_xxxxx",
    "phone_number": "+1-555-0123",
    "turns": 3,
    "responses": [
        {
            "success": True,
            "user_message": "Hi",
            "assistant_response": "Hello!"
        },
        # ... more turns
    ],
    "final_session_info": { ... }
}
```

### Error Response
```python
{
    "success": False,
    "error": "Failed to create session",
    "phone_number": "+1-555-0123"
}
```

---

## 🔌 Session Management

```python
from langchain_session_integration import get_langchain_session_integration

integration = get_langchain_session_integration()

# Get session info
session = integration.get_session_info(session_id)

# Add message manually
integration.add_message_to_session(
    session_id=session_id,
    role="user",
    content="User message"
)

# Manage session
integration.pause_session(session_id)
integration.resume_session(session_id)
integration.terminate_session(session_id)
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```bash
LLM_PROVIDER=openai              # or 'gemini'
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash
MONGODB_URI=mongodb://localhost:27017
```

### Programmatic Configuration
```python
from config.llm_config import get_llm_config

config = get_llm_config()
print(f"Provider: {config.provider}")
print(f"Model: {config.model}")
print(f"Temperature: {config.temperature}")
```

---

## 🧪 Testing

### Unit Test Template
```python
import pytest
from unittest.mock import Mock, patch
from llm_chain_builder import VoiceVerifiedLLMChain

@pytest.mark.asyncio
async def test_process_message():
    mock_llm = Mock()
    mock_llm.invoke = Mock(return_value="Response")
    
    chain = VoiceVerifiedLLMChain(llm=mock_llm)
    result = await chain.process_user_message(
        phone_number="+1-555-0123",
        user_message="Test",
        verification_score=0.95
    )
    
    assert result['success'] is True
```

### Run Tests
```bash
pytest test_langchain_sessions.py -v  # All tests
pytest test_langchain_sessions.py::TestClass::test_name -v  # Specific test
pytest test_langchain_sessions.py -q  # Quiet mode
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError: langchain_google_genai | `pip install langchain-google-generativeai` |
| MongoDB connection error | Ensure MongoDB running at `mongodb://localhost:27017` |
| APIError from LLM provider | Check API key in .env file |
| Session not found | Create new session or check session_id |
| Chain returns empty response | Check LLM_MAX_TOKENS setting |

---

## 📈 Performance Tips

1. **Reuse Chain Instance**
   ```python
   # Good
   chain = VoiceVerifiedLLMChain()
   await chain.process_user_message(...)
   await chain.process_user_message(...)
   
   # Bad - creates new instance each time
   for msg in messages:
       chain = VoiceVerifiedLLMChain()
   ```

2. **Use Async**
   ```python
   # Good - parallel requests
   results = await asyncio.gather(
       chain.process_user_message(...),
       chain.process_user_message(...),
   )
   
   # Bad - sequential requests
   result1 = await chain.process_user_message(...)
   result2 = await chain.process_user_message(...)
   ```

3. **Limit Token Usage**
   ```python
   config = OpenAIConfig(
       max_tokens=500,  # Shorter responses = faster/cheaper
       temperature=0.5  # Lower = more consistent
   )
   ```

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `llm_chain_builder.py` | Main implementation |
| `LLM_CHAIN_BUILDER_GUIDE.md` | Full documentation |
| `test_langchain_sessions.py` | 25 unit tests |
| `.env` | Configuration file |

---

## ✅ Checklist Before Deploy

- [ ] Install dependencies: `pip install langchain langchain-openai`
- [ ] Configure `.env` with API keys
- [ ] Run tests: `pytest test_langchain_sessions.py -v`
- [ ] Test chain: `python llm_chain_builder.py`
- [ ] Set up MongoDB indexes
- [ ] Add to FastAPI routes
- [ ] Configure WebSocket endpoints
- [ ] Add monitoring/logging
- [ ] Test with real voice verification
- [ ] Deploy

---

## 🎯 Next Step

Pick a pattern above, copy the code, and start building! 🚀

For detailed documentation, see: `LLM_CHAIN_BUILDER_GUIDE.md`

---

**Questions?** Check `COMPLETION_SUMMARY_LLM_CHAIN.md` for more details!
