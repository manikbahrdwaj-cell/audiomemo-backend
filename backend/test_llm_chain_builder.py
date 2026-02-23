"""
Quick test of the LLM Chain Builder
Tests the core chain functionality without requiring all LLM provider dependencies
"""

import asyncio
import sys
import os
import logging
from unittest.mock import Mock, patch

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Mock the LLM imports that might fail
def test_llm_chain_builder():
    """Test basic LLM chain builder functionality"""
    
    print("\n" + "="*70)
    print("Testing LLM Chain Builder")
    print("="*70)
    
    # Import with mocked LLM config
    with patch('config.llm_config.get_llm'):
        from llm_chain_builder import VoiceVerifiedLLMChain, RunnableConfigWrapper
        
        print("✓ VoiceVerifiedLLMChain imported successfully")
        
        # Create mock LLM
        mock_llm = Mock()
        mock_llm.invoke = Mock(return_value="Hello! I'm here to help you.")
        
        # Create chain with mock LLM
        chain = VoiceVerifiedLLMChain(llm=mock_llm)
        print("✓ VoiceVerifiedLLMChain initialized")
        
        # Test system prompt creation
        config = RunnableConfigWrapper({
            "configurable": {
                "session_id": "test_session",
                "phone_number": "+1-555-0123",
                "verification_score": 0.95
            }
        })
        
        prompt = chain.create_system_prompt(config)
        assert "test_session" in prompt
        assert "+1-555-0123" in prompt
        print("✓ System prompt creation works")
        
        # Test chain creation
        test_chain = chain.create_chain(config)
        assert test_chain is not None
        print("✓ LLM chain creation works")
        
        print("\n" + "="*70)
        print("✓ All LLM chain builder tests passed!")
        print("="*70)
        print("\nNext steps:")
        print("1. Install langchain_google_genai if using Gemini: pip install langchain-google-generativeai")
        print("2. Configure .env with your LLM provider API keys")
        print("3. Run: python llm_chain_builder.py")
        print("4. Or integrate into your FastAPI routes using VoiceVerifiedLLMChain")

if __name__ == "__main__":
    test_llm_chain_builder()
