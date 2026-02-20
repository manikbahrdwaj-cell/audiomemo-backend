"""
OpenAI Configuration Module
Specialized configuration and utilities for OpenAI API integration
"""

import os
import logging
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)


class OpenAIConfig:
    """
    Specialized configuration for OpenAI models with voice agent optimizations.
    
    Supported models:
    - gpt-4o (latest, recommended) - $15/$60 per 1M tokens
    - gpt-4-turbo - $10/$30 per 1M tokens
    - gpt-4 - $30/$60 per 1M tokens
    - gpt-3.5-turbo - $0.50/$1.50 per 1M tokens
    """
    
    # Default model configuration
    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_TEMPERATURE = 0.1  # Low for deterministic query compilation
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TIMEOUT = 30.0
    
    # Model costs (per 1M tokens) for optimization tracking
    MODEL_COSTS = {
        "gpt-4o": {"input": 15, "output": 60},
        "gpt-4-turbo": {"input": 10, "output": 30},
        "gpt-4": {"input": 30, "output": 60},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: Optional[str] = None
    ):
        """
        Initialize OpenAI configuration.
        
        Args:
            model: OpenAI model name. Defaults to gpt-4o.
            temperature: Sampling temperature (0-2). Lower = more deterministic.
            max_tokens: Maximum tokens in response. Default 4096.
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
        """
        self.model = model or os.environ.get("OPENAI_MODEL", self.DEFAULT_MODEL)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        logger.info(f"OpenAI Config | Model: {self.model} | Temp: {self.temperature}")
    
    def get_llm(self) -> ChatOpenAI:
        """
        Create and return OpenAI ChatOpenAI instance.
        
        Returns:
            ChatOpenAI: Configured OpenAI language model
        """
        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
            request_timeout=self.DEFAULT_TIMEOUT,
            max_retries=2
        )
    
    @staticmethod
    def get_cost_optimized_llm(
        max_budget_per_call: Optional[float] = None
    ) -> ChatOpenAI:
        """
        Get cost-optimized OpenAI LLM based on budget constraints.
        
        Args:
            max_budget_per_call: Maximum budget in dollars for a single API call.
                                If None, uses gpt-4o.
        
        Returns:
            ChatOpenAI: Most cost-effective model within budget
            
        Example:
            >>> # Use cheapest model
            >>> llm = OpenAIConfig.get_cost_optimized_llm(max_budget_per_call=0.01)
        """
        if max_budget_per_call is None:
            # Default to latest/best model
            config = OpenAIConfig()
        else:
            # Select cheapest model within budget
            selected_model = "gpt-3.5-turbo"  # Default to cheapest
            
            for model, costs in OpenAIConfig.MODEL_COSTS.items():
                # Rough estimation: 0.001$ per 16 tokens (simplified)
                avg_cost = (costs["input"] + costs["output"]) / 2 / 1_000_000
                if avg_cost <= max_budget_per_call:
                    selected_model = model
                    break
            
            logger.info(f"Selected cost-optimized model: {selected_model}")
            config = OpenAIConfig(model=selected_model)
        
        return config.get_llm()
    
    @staticmethod
    def create_for_voice_agent(
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> ChatOpenAI:
        """
        Create OpenAI LLM optimized for voice agent query compilation.
        
        Optimizations:
        - Low temperature (0.1) for deterministic results
        - Reasonable token limit for structured queries
        - gpt-4o model for reliable JSON output
        
        Args:
            temperature: Override temperature
            max_tokens: Override max tokens
            
        Returns:
            ChatOpenAI: Optimized for query compilation
        """
        config = OpenAIConfig(
            model="gpt-4o",
            temperature=temperature,
            max_tokens=max_tokens
        )
        return config.get_llm()
    
    @staticmethod
    def create_for_conversation() -> ChatOpenAI:
        """
        Create OpenAI LLM optimized for general conversation.
        
        Optimizations:
        - Temperature 0.7 for more natural responses
        - Larger token limit for detailed responses
        
        Returns:
            ChatOpenAI: Optimized for conversation
        """
        config = OpenAIConfig(
            temperature=0.7,
            max_tokens=4096
        )
        return config.get_llm()


# Convenience functions
def get_openai_llm() -> ChatOpenAI:
    """Get default OpenAI LLM instance."""
    config = OpenAIConfig()
    return config.get_llm()


def get_openai_voice_agent_llm() -> ChatOpenAI:
    """Get OpenAI LLM optimized for voice agent."""
    return OpenAIConfig.create_for_voice_agent()
