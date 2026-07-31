import openai
import groq
from google.genai import errors as google_errors
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings

_TRANSIENT_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
    openai.AuthenticationError,
    openai.BadRequestError,
    groq.RateLimitError,
    groq.APITimeoutError,
    groq.APIConnectionError,
    groq.InternalServerError,
    groq.AuthenticationError,
    groq.BadRequestError,
    google_errors.APIError,
)

from langchain_groq import ChatGroq

google_gemma = ChatGoogleGenerativeAI(
    model=settings.gemma_model,
    google_api_key=settings.google_api_key,
    max_retries=0,
    timeout=60.0,
)

openrouter_nemotron = ChatOpenAI(
    model=settings.openrouter_model,
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
    max_retries=0,
    timeout=60.0,
)

llama_groq = ChatGroq(
    model=settings.groq_fallback_model,
    api_key=settings.groq_api_key,
    max_retries=0,
    timeout=60.0,
)

def get_llm_with_tools(tools: list):
    """Tool-bound fallback chain for the planner node.
    Gemma (Google) -> Nemotron (OpenRouter) -> Llama-3.3 (Groq)."""
    return (
        google_gemma.bind_tools(tools)
        .with_fallbacks(
            [openrouter_nemotron.bind_tools(tools), llama_groq.bind_tools(tools)],
            exceptions_to_handle=_TRANSIENT_EXCEPTIONS,
        )
    )

def get_llm():
    """Plain (no tool binding) fallback chain for the responder node."""
    return google_gemma.with_fallbacks([openrouter_nemotron, llama_groq], exceptions_to_handle=_TRANSIENT_EXCEPTIONS)
