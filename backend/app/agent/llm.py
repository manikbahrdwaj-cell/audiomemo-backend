from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings


def build_llm() -> BaseChatModel:
    """Instantiate and return the configured chat LLM.

    The provider is chosen via ``settings.LLM_PROVIDER``:

    * ``"openai"``  → :class:`~langchain_openai.ChatOpenAI` (gpt-4o-mini)
    * ``"gemini"``  → :class:`~langchain_google_vertexai.ChatVertexAI` (gemini-1.5-flash)

    Raises:
        ValueError: If ``LLM_PROVIDER`` is set to an unrecognised value.

    Note:
        This function is intentionally **not** cached at module level.
        ``graph.py`` calls it once at compile time so the graph always
        picks up the settings present at startup.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)

    if provider == "gemini":
        from langchain_google_vertexai import ChatVertexAI

        return ChatVertexAI(model="gemini-1.5-flash", project=settings.GOOGLE_PROJECT_ID)

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}")
