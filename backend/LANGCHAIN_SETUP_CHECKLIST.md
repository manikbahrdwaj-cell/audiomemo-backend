"""
LangChain Integration Checklist
Verify your LangChain setup is complete and working
"""

# LangChain Integration Checklist

## Pre-Setup Checklist

### API Keys
- [ ] Have OpenAI API key (if using OpenAI)
  - Get from: https://platform.openai.com/account/api-keys
- [ ] Have Google API key (if using Gemini)
  - Get from: https://makersuite.google.com/app/apikey
- [ ] API key format is correct
  - OpenAI: starts with `sk-`
  - Google: starts with `AIza`

### Environment
- [ ] Python 3.14+ installed
- [ ] Virtual environment activated
  - Windows: `.\venv\Scripts\activate`
  - Mac/Linux: `source venv/bin/activate`

---

## Installation Checklist

### Dependencies
- [ ] Run `pip install -r requirements.txt`
- [ ] No errors during installation
- [ ] All packages installed:
  ```bash
  python -c "import langchain; print(langchain.__version__)"
  ```
  Expected: `1.2.10` or higher

### Configuration Files
- [ ] `config/llm_config.py` exists
- [ ] `config/openai_config.py` exists
- [ ] `config/gemini_config.py` exists
- [ ] `config/__init__.py` exists
- [ ] All files have no syntax errors

---

## Configuration Checklist

### .env File
- [ ] Created `.env` file from `.env.example`
- [ ] Located in `backend/` directory
- [ ] Contains API key(s):
  - [ ] `OPENAI_API_KEY` (if using OpenAI)
  - [ ] `GOOGLE_API_KEY` (if using Gemini)
- [ ] Set `LLM_PROVIDER` (openai or gemini)
- [ ] Set `LLM_TEMPERATURE=0.1`
- [ ] Set `LLM_MAX_TOKENS=4096`

### API Key Verification
- [ ] API key is correct (copy-paste from provider dashboard)
- [ ] API key hasn't been regenerated/revoked
- [ ] Account has billing enabled
- [ ] No typos in `.env`

---

## Testing Checklist

### Basic Imports
Run in Python:
```python
from config.llm_config import get_llm
from langchain_core.messages import HumanMessage
print("Imports successful!")
```

- [ ] Imports work without errors

### Test LLM
Run in Python:
```python
from config.llm_config import get_llm
from langchain_core.messages import HumanMessage

llm = get_llm()
response = llm.invoke([HumanMessage(content="Hello")])
print(response.content[:50])
```

- [ ] No "API key not found" error
- [ ] No "Connection refused" error
- [ ] Got response from LLM
- [ ] Response is not empty

### Test Examples
Run `langchain_integration_examples.py`:
```bash
python langchain_integration_examples.py
```

- [ ] Script runs without errors
- [ ] All 10 examples complete
- [ ] Examples show expected output

### Provider-Specific Tests

#### OpenAI
```python
from config.openai_config import get_openai_llm
llm = get_openai_llm()
# Should not raise error
```
- [ ] OpenAI LLM created successfully

#### Gemini
```python
from config.gemini_config import get_gemini_llm
llm = get_gemini_llm()
# Should not raise error
```
- [ ] Gemini LLM created successfully

---

## Integration Checklist

### FastAPI Integration
- [ ] Can import `get_llm()` in FastAPI routes
- [ ] Routes execute without import errors
- [ ] API endpoints return LLM responses

### WebSocket Integration
- [ ] Can use `get_llm()` in WebSocket handlers
- [ ] WebSocket connections don't fail on LLM initialization
- [ ] Messages are processed correctly

### Database Integration
- [ ] LLM responses can be stored in MongoDB
- [ ] Query compilation with LLM works
- [ ] Results match expected format

---

## Performance Checklist

### Response Time
- [ ] First response within 5 seconds
- [ ] Subsequent responses within 2-3 seconds
- [ ] No timeouts

### Token Usage
- [ ] Monitor token usage in OpenAI/Gemini dashboard
- [ ] Actual tokens match expected count
- [ ] Stay within budget

### Error Handling
- [ ] API errors handled gracefully
- [ ] Clear error messages displayed
- [ ] Application doesn't crash on LLM error

---

## Security Checklist

### API Key Security
- [ ] `.env` file is NOT committed to git
- [ ] `.gitignore` includes `.env`
- [ ] API key not logged in debug output
- [ ] API key not sent in frontend

### Environment Variable Safety
- [ ] Use environment variables for all secrets
- [ ] No hardcoded API keys in code
- [ ] Different keys for dev/prod if needed

---

## Production Readiness Checklist

### Logging
- [ ] All LLM calls are logged
- [ ] Errors are properly logged
- [ ] Log files stored securely

### Monitoring
- [ ] Token usage is monitored
- [ ] Cost tracking enabled
- [ ] Alerts set for unusual activity

### Documentation
- [ ] Team familiar with configuration
- [ ] Documentation accessible
- [ ] Runbook for troubleshooting exists

### Testing
- [ ] Unit tests written for LLM calls
- [ ] Integration tests pass
- [ ] Performance tests baseline established

---

## Troubleshooting Checklist

### "API key not found" Error
- [ ] `.env` file exists in `backend/` directory
- [ ] Python is reading `.env` (use `dotenv`)
- [ ] API key variable name matches (OPENAI_API_KEY or GOOGLE_API_KEY)
- [ ] API key has no leading/trailing spaces

### "Connection refused" Error
- [ ] Internet connection is working
- [ ] API provider is not down (check status page)
- [ ] Firewall not blocking API calls
- [ ] Proxy settings correct if behind corporate proxy

### "Rate limit exceeded" Error
- [ ] Check API provider's rate limit
- [ ] Add delay between requests
- [ ] Consider upgrading to paid tier
- [ ] Implement exponential backoff

### "Token limit exceeded" Error
- [ ] Reduce `LLM_MAX_TOKENS` in `.env`
- [ ] Use cheaper/faster model
- [ ] Split large requests into smaller ones
- [ ] Use Gemini for long context (1M tokens)

### "Module not found" Error
- [ ] Run `pip install -r requirements.txt` again
- [ ] Virtual environment is activated
- [ ] Installation completed without errors
- [ ] Check `pip list | grep langchain`

---

## Optimization Checklist

### Cost Optimization
- [ ] Using cost-optimal model for use case
- [ ] Temperature set appropriately (0.1 for deterministic)
- [ ] Max tokens minimized where possible
- [ ] Monitor usage in provider dashboard

### Speed Optimization
- [ ] Using fast model (gemini-2.0-flash or gpt-4o)
- [ ] Request timeout set appropriately
- [ ] Connection pooling enabled
- [ ] Response streaming for long outputs

### Resource Optimization
- [ ] Memory usage is reasonable
- [ ] No memory leaks in application
- [ ] CPU usage is acceptable
- [ ] Connection limits respected

---

## Documentation Checklist

- [ ] Read `LANGCHAIN_QUICK_START.md`
- [ ] Read `LANGCHAIN_INTEGRATION_GUIDE.md`
- [ ] Reviewed `langchain_integration_examples.py`
- [ ] Understood `.env.example` configuration
- [ ] Know how to switch providers

---

## Final Verification

Run this script to verify everything:

```python
#!/usr/bin/env python3
"""LangChain Setup Verification Script"""

import os
import sys

def check(description):
    def decorator(func):
        try:
            result = func()
            status = "OK" if result else "FAIL"
            print(f"[{status}] {description}")
            return result
        except Exception as e:
            print(f"[ERROR] {description}: {str(e)[:50]}")
            return False
    return decorator

# Run checks
print("\n=== LangChain Setup Verification ===\n")

@check("Environment setup")
def _():
    return os.path.exists('.env')

@check("Langchain import")
def _():
    import langchain
    return True

@check("OpenAI provider")
def _():
    from langchain_openai import ChatOpenAI
    return True

@check("Gemini provider")
def _():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return True

@check("Config module")
def _():
    from config.llm_config import get_llm
    return True

@check("LLM instantiation")
def _():
    from config.llm_config import get_llm
    llm = get_llm()
    return llm is not None

print("\n=== Verification Complete ===\n")
```

---

## Success Criteria

You're ready when:
- ✓ All items are checked
- ✓ Example script runs without errors
- ✓ LLM responds to test queries
- ✓ Can integrate into FastAPI routes
- ✓ Documentation is understood
- ✓ Team is trained

---

## Support

If you encounter issues:

1. Check troubleshooting section above
2. Review `LANGCHAIN_INTEGRATION_GUIDE.md`
3. Run verification script
4. Check API provider status
5. Review logs for error details
6. Contact support (include error message and `.env` summary)

---

## Quick Links

- OpenAI API: https://platform.openai.com/account/api-keys
- Gemini API: https://makersuite.google.com/app/apikey
- OpenAI Docs: https://platform.openai.com/docs/
- Gemini Docs: https://ai.google.dev/docs
- LangChain Docs: https://python.langchain.com/docs/

---

**Last Updated:** February 19, 2026  
**Status:** Ready for Production
