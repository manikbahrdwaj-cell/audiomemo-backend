"""
Google Gemini Configuration Module
Specialized configuration and utilities for Google Gemini API integration
"""

import os
import logging
from typing import Optional, List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)


class GeminiConfig:
    """
    Specialized configuration for Google Gemini models with voice agent optimizations.
    
    Supported models:
    - gemini-2.0-flash (latest, recommended) - 1M context window, fastest
    - gemini-1.5-pro - 1M context window, most capable
    - gemini-1.5-flash - 1M context window, balanced
    
    Pricing:
    - Gemini 2.0 Flash: $0.075 / 1M input tokens, $0.30 / 1M output tokens
    - Gemini 1.5 Pro: $3.50 / 1M input tokens, $10.50 / 1M output tokens
    - Gemini 1.5 Flash: $0.075 / 1M input tokens, $0.30 / 1M output tokens
    """
    
    # Default model configuration
    DEFAULT_MODEL = "gemini-2.0-flash"
    DEFAULT_TEMPERATURE = 0.1  # Low for deterministic query compilation
    DEFAULT_MAX_TOKENS = 4096
    
    # Safety settings for Gemini - blocking only high-risk content
    SAFETY_SETTINGS = [
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_UNSPECIFIED",
            "threshold": "BLOCK_ONLY_HIGH"
        }
    ]
    
    # Model costs (per 1M tokens) for optimization tracking
    MODEL_COSTS = {
        "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    }
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: Optional[str] = None
    ):
        """
        Initialize Gemini configuration.
        
        Args:
            model: Gemini model name. Defaults to gemini-2.0-flash.
            temperature: Sampling temperature (0-2). Lower = more deterministic.
            max_tokens: Maximum tokens in response. Default 4096.
            api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.
        """
        self.model = model or os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        logger.info(f"Gemini Config | Model: {self.model} | Temp: {self.temperature}")
    
    def get_llm(self) -> ChatGoogleGenerativeAI:
        """
        Create and return Gemini ChatGoogleGenerativeAI instance.
        
        Returns:
            ChatGoogleGenerativeAI: Configured Gemini language model
        """
        return ChatGoogleGenerativeAI(
            model=self.model,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            top_p=0.95,
            top_k=40,
            google_api_key=self.api_key,
            convert_system_message_to_human=True,  # IMPORTANT: Gemini requirement
            safety_settings=self.SAFETY_SETTINGS
        )
    
    @staticmethod
    def get_cost_optimized_llm(
        max_budget_per_call: Optional[float] = None
    ) -> ChatGoogleGenerativeAI:
        """
        Get cost-optimized Gemini LLM based on budget constraints.
        
        Args:
            max_budget_per_call: Maximum budget in dollars for a single API call.
                                If None, uses gemini-2.0-flash.
        
        Returns:
            ChatGoogleGenerativeAI: Most cost-effective model within budget
            
        Example:
            >>> # Use cheapest model
            >>> llm = GeminiConfig.get_cost_optimized_llm(max_budget_per_call=0.01)
        """
        if max_budget_per_call is None:
            # Default to latest/best model
            config = GeminiConfig()
        else:
            # Select cheapest model within budget
            selected_model = "gemini-2.0-flash"  # Default to cheapest in Gemini
            
            for model, costs in GeminiConfig.MODEL_COSTS.items():
                # Rough estimation: cost per token
                avg_cost = (costs["input"] + costs["output"]) / 2 / 1_000_000
                if avg_cost <= max_budget_per_call:
                    selected_model = model
                    break
            
            logger.info(f"Selected cost-optimized model: {selected_model}")
            config = GeminiConfig(model=selected_model)
        
        return config.get_llm()
    
    @staticmethod
    def create_for_voice_agent(
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> ChatGoogleGenerativeAI:
        """
        Create Gemini LLM optimized for voice agent query compilation.
        
        Optimizations:
        - Low temperature (0.1) for deterministic results
        - Reasonable token limit for structured queries
        - gemini-2.0-flash model for fastest inference
        - System message converted to human format (Gemini requirement)
        
        Args:
            temperature: Override temperature
            max_tokens: Override max tokens
            
        Returns:
            ChatGoogleGenerativeAI: Optimized for query compilation
        """
        config = GeminiConfig(
            model="gemini-2.0-flash",
            temperature=temperature,
            max_tokens=max_tokens
        )
        return config.get_llm()
    
    @staticmethod
    def create_for_conversation() -> ChatGoogleGenerativeAI:
        """
        Create Gemini LLM optimized for general conversation.
        
        Optimizations:
        - Temperature 0.7 for more natural responses
        - Larger token limit for detailed responses
        - Can handle extended context (1M tokens)
        
        Returns:
            ChatGoogleGenerativeAI: Optimized for conversation
        """
        config = GeminiConfig(
            temperature=0.7,
            max_tokens=4096
        )
        return config.get_llm()
    
    @staticmethod
    def create_for_long_context(
        temperature: float = 0.5,
        max_tokens: int = 4096
    ) -> ChatGoogleGenerativeAI:
        """
        Create Gemini LLM optimized for long-context processing.
        
        Note: Gemini supports up to 1M token context window.
        
        Args:
            temperature: Override temperature
            max_tokens: Override max tokens
            
        Returns:
            ChatGoogleGenerativeAI: Optimized for long context
        """
        config = GeminiConfig(
            model="gemini-1.5-pro",  # Better for long context
            temperature=temperature,
            max_tokens=max_tokens
        )
        return config.get_llm()


# Convenience functions
def get_gemini_llm() -> ChatGoogleGenerativeAI:
    """Get default Gemini LLM instance."""
    config = GeminiConfig()
    return config.get_llm()


def get_gemini_voice_agent_llm() -> ChatGoogleGenerativeAI:
    """Get Gemini LLM optimized for voice agent."""
    return GeminiConfig.create_for_voice_agent()


def get_gemini_conversation_llm() -> ChatGoogleGenerativeAI:
    """Get Gemini LLM optimized for conversation."""
    return GeminiConfig.create_for_conversation()
