"""
LLM Configuration Module
Centralized management for LLM providers (OpenAI, Google Gemini, etc.)
"""

import os
from typing import Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
import logging

logger = logging.getLogger(__name__)


class LLMConfig:
    """
    Centralized LLM configuration management.
    Supports multiple providers with environment-based switching.
    
    Supported providers:
    - openai: GPT-4, GPT-4 Turbo, GPT-3.5
    - gemini: Gemini 2.0 Flash, Gemini 1.5 Pro
    """
    
    def __init__(self):
        """Initialize LLM configuration from environment variables."""
        self.provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        self.model = self._get_model_name()
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4000"))
        self.top_p = float(os.environ.get("LLM_TOP_P", "0.95"))
        
        logger.info(f"LLM Config initialized | Provider: {self.provider} | Model: {self.model}")
    
    def _get_model_name(self) -> str:
        """Get model name based on provider configuration."""
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openai":
            model = os.environ.get("OPENAI_MODEL", "gpt-4o")
            logger.debug(f"Using OpenAI model: {model}")
            return model
        elif provider == "gemini":
            model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
            logger.debug(f"Using Gemini model: {model}")
            return model
        else:
            logger.warning(f"Unknown provider: {provider}, defaulting to openai/gpt-4o")
            return os.environ.get("OPENAI_MODEL", "gpt-4o")
    
    def get_llm(self) -> BaseChatModel:
        """
        Factory method to create appropriate LLM instance.
        
        Returns:
            BaseChatModel: Configured LLM instance (ChatOpenAI or ChatGoogleGenerativeAI)
            
        Raises:
            ValueError: If required API keys are not configured
        """
        if self.provider == "openai":
            return self._get_openai_llm()
        elif self.provider == "gemini":
            return self._get_gemini_llm()
        else:
            logger.warning(f"Unknown provider: {self.provider}, falling back to OpenAI")
            return self._get_openai_llm()
    
    def _get_openai_llm(self) -> ChatOpenAI:
        """Create and configure OpenAI LLM instance."""
        api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please set it to use OpenAI provider."
            )
        
        logger.info("Initializing OpenAI LLM")
        
        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            api_key=api_key,
            request_timeout=30.0,  # 30 second timeout
            max_retries=2
        )
    
    def _get_gemini_llm(self) -> ChatGoogleGenerativeAI:
        """Create and configure Google Gemini LLM instance."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable not set. "
                "Please set it to use Gemini provider."
            )
        
        logger.info("Initializing Google Gemini LLM")
        
        return ChatGoogleGenerativeAI(
            model=self.model,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            top_p=self.top_p,
            google_api_key=api_key,
            convert_system_message_to_human=True  # Gemini requires human message format
        )
    
    @staticmethod
    def create_llm(provider: Optional[str] = None) -> BaseChatModel:
        """
        Create LLM instance directly with optional provider override.
        
        Args:
            provider: Provider name ('openai' or 'gemini'). If None, uses env var.
            
        Returns:
            BaseChatModel: Configured LLM instance
        """
        if provider:
            os.environ["LLM_PROVIDER"] = provider
        
        config = LLMConfig()
        return config.get_llm()


# Global LLM configuration instance
_llm_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """
    Get or create global LLM configuration instance (singleton pattern).
    
    Returns:
        LLMConfig: Global LLM configuration
    """
    global _llm_config
    if _llm_config is None:
        _llm_config = LLMConfig()
    return _llm_config


def get_llm() -> BaseChatModel:
    """
    Get configured LLM instance.
    
    Returns:
        BaseChatModel: Configured LLM for use in agents and chains
        
    Usage:
        >>> from config.llm_config import get_llm
        >>> llm = get_llm()
        >>> response = llm.invoke([HumanMessage(content="Hello")])
    """
    config = get_llm_config()
    return config.get_llm()


def reset_llm_config():
    """Reset the global LLM configuration (useful for testing)."""
    global _llm_config
    _llm_config = None
