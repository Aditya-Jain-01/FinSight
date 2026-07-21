"""LLM Factory: creates a primary Gemini LLM with optional Groq and NVIDIA NIM fallbacks.

Usage:
    from app.agent.llm_factory import get_llm_with_fallbacks

    # For the planner (needs tool calling):
    llm = get_llm_with_fallbacks(tools=TOOLS, temperature=0)

    # For the responder (no tools):
    llm = get_llm_with_fallbacks(temperature=0.3)

Key design decisions:
- Tools are bound to EACH model individually BEFORE calling with_fallbacks().
  This is required because with_fallbacks() proxies calls to the underlying
  model, and tool binding must happen at the individual model level.
- Fallback providers are only wired up if their API key is configured.
  If no fallback keys are set, Gemini runs alone with no fallback chain.
- Provider metadata is extracted from response.response_metadata after invocation.
"""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

logger = logging.getLogger(__name__)


def _create_gemini(temperature: float) -> ChatGoogleGenerativeAI:
    """Create the primary Gemini LLM."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
    )


def _create_groq(temperature: float) -> BaseChatModel | None:
    """Create the Groq fallback LLM, or None if no API key is configured."""
    if not settings.groq_api_key:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
        )
    except ImportError:
        logger.warning("langchain-groq not installed — Groq fallback disabled")
        return None


def _create_nvidia(temperature: float) -> BaseChatModel | None:
    """Create the NVIDIA NIM fallback LLM, or None if no API key is configured."""
    if not settings.nvidia_api_key:
        return None
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            temperature=temperature,
        )
    except ImportError:
        logger.warning("langchain-nvidia-ai-endpoints not installed — NVIDIA fallback disabled")
        return None


def get_llm_with_fallbacks(
    *,
    tools: list[Any] | None = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    """Create a Gemini LLM with optional Groq and NVIDIA NIM fallbacks.

    Args:
        tools: If provided, bind these tools to each model before chaining.
               Tools are bound INDIVIDUALLY to each model, then with_fallbacks()
               is called on the already-bound models.
        temperature: LLM temperature (0 for planner, 0.3 for responder).

    Returns:
        A LangChain chat model. If fallback keys are configured, this is a
        RunnableWithFallbacks wrapping Gemini → Groq → NVIDIA.
        If no fallback keys are set, this is just the bare Gemini model.
    """
    # 1. Create all available models
    gemini = _create_gemini(temperature)
    groq = _create_groq(temperature)
    nvidia = _create_nvidia(temperature)

    # 2. Bind tools to each model individually (BEFORE with_fallbacks)
    if tools:
        gemini = gemini.bind_tools(tools)
        if groq:
            groq = groq.bind_tools(tools)
        if nvidia:
            nvidia = nvidia.bind_tools(tools)

    # 3. Build the fallback chain
    fallbacks = [m for m in [groq, nvidia] if m is not None]

    if fallbacks:
        providers = ["Gemini"] + (["Groq"] if groq else []) + (["NVIDIA"] if nvidia else [])
        logger.info(f"LLM fallback chain: {' → '.join(providers)}")
        return gemini.with_fallbacks(fallbacks)
    else:
        logger.info("LLM: Gemini only (no fallback keys configured)")
        return gemini


def extract_provider_metadata(response) -> dict:
    """Extract provider/model information from an LLM response.

    Works with any LangChain AIMessage. Returns a dict with:
    - provider: str (e.g. "Gemini", "Groq", "NVIDIA")
    - model: str (e.g. "gemini-3.5-flash", "llama-3.3-70b-versatile")
    - fallback_used: bool
    """
    meta = getattr(response, "response_metadata", {}) or {}

    # Try to identify the provider from response metadata
    model_name = meta.get("model_name") or meta.get("model", "")

    # Gemini responses have a "model_name" like "gemini-3.5-flash"
    # Groq responses have "model_name" like "llama-3.3-70b-versatile"
    # NVIDIA responses have "model_name" like "meta/llama-3.3-70b-instruct"

    if "gemini" in model_name.lower():
        provider = "Gemini"
        fallback_used = False
    elif "/" in model_name:
        # NVIDIA models use org/model format (e.g. "meta/llama-3.3-70b-instruct")
        provider = "NVIDIA"
        fallback_used = True
    elif model_name:
        # Groq models are plain names (e.g. "llama-3.3-70b-versatile")
        provider = "Groq"
        fallback_used = True
    else:
        provider = "Unknown"
        fallback_used = False

    return {
        "provider": provider,
        "model": model_name or settings.gemini_model,
        "fallback_used": fallback_used,
    }
