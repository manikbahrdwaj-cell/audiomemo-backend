"""
LangChain Integration Examples for Voice Biometric Authentication
Demonstrates how to use OpenAI, Gemini, and other LLM providers
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# LangChain imports
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

# Local imports
from config.llm_config import get_llm, get_llm_config
from config.openai_config import OpenAIConfig, get_openai_voice_agent_llm
from config.gemini_config import GeminiConfig, get_gemini_voice_agent_llm

logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Basic LLM Usage
# ============================================================================

def example_1_basic_llm_usage():
    """
    Example 1: Basic usage of any LLM (OpenAI or Gemini)
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic LLM Usage")
    print("="*70)
    
    # Get the configured LLM (uses LLM_PROVIDER from .env)
    llm = get_llm()
    
    # Create a simple message
    message = HumanMessage(content="What is voice biometric authentication?")
    
    # Invoke the LLM
    response = llm.invoke([message])
    
    print(f"User: What is voice biometric authentication?")
    print(f"AI: {response.content}")


# ============================================================================
# EXAMPLE 2: OpenAI Configuration
# ============================================================================

def example_2_openai_specific():
    """
    Example 2: Using OpenAI-specific configuration
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: OpenAI Configuration")
    print("="*70)
    
    # Option 1: Using OpenAIConfig directly
    config = OpenAIConfig(model="gpt-4o")
    llm = config.get_llm()
    
    # Option 2: Using convenience function
    llm = OpenAIConfig.create_for_voice_agent()
    
    # Option 3: Get cost-optimized model
    # llm = OpenAIConfig.get_cost_optimized_llm(max_budget_per_call=0.01)
    
    message = HumanMessage(
        content="Compile this into a MongoDB query: Show me recent enrollments"
    )
    
    response = llm.invoke([message])
    print(f"Response: {response.content}")


# ============================================================================
# EXAMPLE 3: Gemini Configuration
# ============================================================================

def example_3_gemini_specific():
    """
    Example 3: Using Google Gemini-specific configuration
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Gemini Configuration")
    print("="*70)
    
    # Option 1: Using GeminiConfig directly
    config = GeminiConfig(model="gemini-2.0-flash")
    llm = config.get_llm()
    
    # Option 2: Using convenience function
    llm = GeminiConfig.create_for_voice_agent()
    
    # Option 3: Get cost-optimized model
    # llm = GeminiConfig.get_cost_optimized_llm(max_budget_per_call=0.01)
    
    message = HumanMessage(
        content="Compile this into a MongoDB query: Get my recent voice verifications"
    )
    
    response = llm.invoke([message])
    print(f"Response: {response.content}")


# ============================================================================
# EXAMPLE 4: Prompt Templates with Voice Agent
# ============================================================================

def example_4_prompt_templates():
    """
    Example 4: Using LangChain prompt templates for voice agent
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Prompt Templates")
    print("="*70)
    
    llm = get_openai_voice_agent_llm()
    
    # Create prompt template for query compilation
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "You are a MongoDB query compiler for a voice biometric system. "
            "Convert user requests into MongoDB query JSON. "
            "Always include user_id in filters for security."
        ),
        HumanMessagePromptTemplate.from_template(
            "User ID: {user_id}\nUser Request: {request}"
        )
    ])
    
    # Create chain
    chain = prompt | llm
    
    # Invoke
    result = chain.invoke({
        "user_id": "user_123",
        "request": "Show my recent voice enrollments"
    })
    
    print(f"Compiled Query:\n{result.content}")


# ============================================================================
# EXAMPLE 5: Voice Authentication Query Compilation
# ============================================================================

def example_5_voice_query_compilation():
    """
    Example 5: Compile natural language to MongoDB queries for voice system
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Voice Authentication Query Compilation")
    print("="*70)
    
    llm = OpenAIConfig.create_for_voice_agent()
    
    # System message for query compilation
    system_msg = SystemMessage(
        content="""You are a MongoDB query compiler for voice biometric authentication.
        
Your task: Convert natural language requests into MongoDB query JSON.

Important rules:
1. Always include user_id for security
2. Return valid JSON only
3. Use appropriate MongoDB operators ($gte, $lte, $in, etc.)
4. Focus on the orders and enrollments collections

Examples:
- "Show my enrollments" → {"collection": "enrollments", "filter": {"user_id": "USER_ID"}}
- "Recent verifications" → {"collection": "verifications", "filter": {"user_id": "USER_ID", "timestamp": {"$gte": ISODate("2026-02-10")}}}
"""
    )
    
    # User request
    user_request = "Show me all successful voice verifications from the last week"
    user_msg = HumanMessage(content=user_request)
    
    # Get compiled query
    response = llm.invoke([system_msg, user_msg])
    
    print(f"User Request: {user_request}")
    print(f"Compiled Query:\n{response.content}")


# ============================================================================
# EXAMPLE 6: Multi-turn Conversation
# ============================================================================

def example_6_conversation_history():
    """
    Example 6: Multi-turn conversation with message history
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: Multi-turn Conversation")
    print("="*70)
    
    llm = GeminiConfig.create_for_conversation()
    
    # Conversation history
    conversation = [
        SystemMessage(
            content="You are a voice authentication support assistant. "
                   "Help users with voice verification issues."
        ),
        HumanMessage(content="How do I enroll my voice?"),
        AIMessage(content="To enroll your voice, please: 1. Upload a WAV file, "
                         "2. Say your security phrase, 3. Verify success message."),
        HumanMessage(content="What if it says the voice doesn't match?"),
    ]
    
    # Get response
    response = llm.invoke(conversation)
    
    print("Assistant:", response.content)


# ============================================================================
# EXAMPLE 7: Using LangChain Chains for Voice Processing
# ============================================================================

def example_7_voice_chain():
    """
    Example 7: Create a chain for voice biometric processing
    """
    print("\n" + "="*70)
    print("EXAMPLE 7: Voice Processing Chain")
    print("="*70)
    
    llm = get_openai_voice_agent_llm()
    
    # Step 1: Analyze voice enrollment quality
    analysis_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "Analyze voice quality metrics and provide enrollment recommendation"
        ),
        HumanMessagePromptTemplate.from_template(
            "Sample rate: {sample_rate}Hz\n"
            "Duration: {duration}s\n"
            "Noise level: {noise_level}dB\n"
            "Background noise: {background_noise}"
        )
    ])
    
    analysis_chain = analysis_prompt | llm
    
    # Step 2: Generate analysis
    result = analysis_chain.invoke({
        "sample_rate": 16000,
        "duration": 5,
        "noise_level": 20,
        "background_noise": "minimal"
    })
    
    print(f"Voice Quality Analysis:\n{result.content}")


# ============================================================================
# EXAMPLE 8: Error Handling and Retry Logic
# ============================================================================

def example_8_error_handling():
    """
    Example 8: Proper error handling for LLM calls
    """
    print("\n" + "="*70)
    print("EXAMPLE 8: Error Handling")
    print("="*70)
    
    try:
        llm = get_llm()
        
        # Attempt 1: Try the request
        try:
            message = HumanMessage(content="Process voice verification")
            response = llm.invoke([message])
            print(f"Success: {response.content[:100]}...")
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            print(f"Error calling LLM: {type(e).__name__}")
            
            # Fallback: Use simpler model
            print("Falling back to backup LLM...")
            try:
                config = get_llm_config()
                if config.provider == "openai":
                    llm = OpenAIConfig(model="gpt-3.5-turbo").get_llm()
                else:
                    llm = GeminiConfig(model="gemini-2.0-flash").get_llm()
                
                response = llm.invoke([message])
                print(f"Fallback Success: {response.content[:100]}...")
                
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                print(f"Error with fallback: {type(e2).__name__}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")


# ============================================================================
# EXAMPLE 9: Batch Processing Voice Requests
# ============================================================================

def example_9_batch_processing():
    """
    Example 9: Batch process multiple voice requests
    """
    print("\n" + "="*70)
    print("EXAMPLE 9: Batch Processing")
    print("="*70)
    
    llm = OpenAIConfig.create_for_voice_agent()
    
    # Batch requests
    requests = [
        "Show my recent enrollments",
        "Get verification statistics",
        "List failed verifications from today"
    ]
    
    print("Processing batch requests:")
    for i, request in enumerate(requests, 1):
        try:
            prompt = f"Compile to MongoDB query: {request}"
            message = HumanMessage(content=prompt)
            response = llm.invoke([message])
            print(f"{i}. {request}")
            print(f"   Query: {response.content[:80]}...\n")
        except Exception as e:
            print(f"{i}. {request}")
            print(f"   Error: {e}\n")


# ============================================================================
# EXAMPLE 10: Provider Switching at Runtime
# ============================================================================

def example_10_provider_switching():
    """
    Example 10: Switch between providers at runtime
    """
    print("\n" + "="*70)
    print("EXAMPLE 10: Provider Switching")
    print("="*70)
    
    test_message = "What is the similarity threshold for voice verification?"
    
    # Test with OpenAI
    print("Testing with OpenAI:")
    os.environ["LLM_PROVIDER"] = "openai"
    try:
        from config.llm_config import reset_llm_config
        reset_llm_config()
        llm = get_llm()
        response = llm.invoke([HumanMessage(content=test_message)])
        print(f"OpenAI: {response.content[:80]}...")
    except Exception as e:
        print(f"OpenAI Error: {e}")
    
    # Test with Gemini
    print("\nTesting with Gemini:")
    os.environ["LLM_PROVIDER"] = "gemini"
    try:
        from config.llm_config import reset_llm_config
        reset_llm_config()
        llm = get_llm()
        response = llm.invoke([HumanMessage(content=test_message)])
        print(f"Gemini: {response.content[:80]}...")
    except Exception as e:
        print(f"Gemini Error: {e}")


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Run all examples"""
    logging.basicConfig(level=logging.INFO)
    
    examples = [
        ("Basic LLM Usage", example_1_basic_llm_usage),
        ("OpenAI Configuration", example_2_openai_specific),
        ("Gemini Configuration", example_3_gemini_specific),
        ("Prompt Templates", example_4_prompt_templates),
        ("Voice Query Compilation", example_5_voice_query_compilation),
        ("Conversation History", example_6_conversation_history),
        ("Voice Processing Chain", example_7_voice_chain),
        ("Error Handling", example_8_error_handling),
        ("Batch Processing", example_9_batch_processing),
        ("Provider Switching", example_10_provider_switching),
    ]
    
    print("\n" + "="*70)
    print("LangChain Integration Examples for Voice Authentication")
    print("="*70)
    
    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\n" + "="*70)
    
    # Run example based on user choice or all if running directly
    import sys
    if len(sys.argv) > 1:
        try:
            choice = int(sys.argv[1]) - 1
            if 0 <= choice < len(examples):
                examples[choice][1]()
            else:
                print(f"Invalid choice. Please select 1-{len(examples)}")
        except ValueError:
            print("Invalid input. Please provide a number.")
    else:
        # Run all examples with error handling
        for name, example_func in examples:
            try:
                example_func()
            except Exception as e:
                print(f"\n❌ Error in {name}: {e}")
                logger.exception(f"Error in {name}")


if __name__ == "__main__":
    main()
