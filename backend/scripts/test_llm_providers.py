"""Test each LLM provider independently for tool-calling compatibility.

Usage:
    cd backend
    python -m scripts.test_llm_providers

Tests Gemini, Groq, and NVIDIA NIM individually. For each provider:
- Binds the project's existing tools
- Runs several realistic financial prompts
- Validates that the model issues tool calls (not just text answers)
- Reports latency, tool names, and arguments
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.agent.tools.registry import TOOLS
from app.agent.nodes.planner import PLANNER_SYSTEM_PROMPT

# Test prompts that should trigger tool calling
TEST_PROMPTS = [
    ("What is Apple's current stock price?", ["get_stock_price"]),
    ("Compare Microsoft and Apple P/E ratios.", ["get_financials"]),
    ("Summarize the latest filing for Reliance.", ["rag_search"]),
    ("Show NVIDIA revenue growth.", ["get_financials", "get_stock_price"]),
]


def _create_providers() -> list[tuple[str, str, object]]:
    """Create all available providers with tools bound."""
    providers = []

    # Gemini (always available — it's the primary)
    from langchain_google_genai import ChatGoogleGenerativeAI
    gemini = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0,
    ).bind_tools(TOOLS)
    providers.append(("Gemini", settings.gemini_model, gemini))

    # Groq (optional)
    if settings.groq_api_key:
        try:
            from langchain_groq import ChatGroq
            groq = ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                temperature=0,
            ).bind_tools(TOOLS)
            providers.append(("Groq", settings.groq_model, groq))
        except ImportError:
            print("⚠️  langchain-groq not installed — skipping Groq\n")
    else:
        print("⚠️  GROQ_API_KEY not set — skipping Groq\n")

    # NVIDIA (optional)
    if settings.nvidia_api_key:
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            nvidia = ChatNVIDIA(
                model=settings.nvidia_model,
                api_key=settings.nvidia_api_key,
                temperature=0,
            ).bind_tools(TOOLS)
            providers.append(("NVIDIA", settings.nvidia_model, nvidia))
        except ImportError:
            print("⚠️  langchain-nvidia-ai-endpoints not installed — skipping NVIDIA\n")
    else:
        print("⚠️  NVIDIA_API_KEY not set — skipping NVIDIA\n")

    return providers


async def test_provider(provider_name: str, model_name: str, llm, prompt: str, expected_tools: list[str]):
    """Test a single prompt against a single provider."""
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    start = time.monotonic()
    try:
        response = await llm.ainvoke(messages)
        latency_ms = round((time.monotonic() - start) * 1000)
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

    tool_calls = getattr(response, "tool_calls", None) or []

    if not tool_calls:
        print(f"  ❌ FAILED: Model did not perform tool calling.")
        print(f"     Response text: {str(response.content)[:200]}")
        print(f"     Latency: {latency_ms}ms")
        return False

    print(f"  ✅ Tool calls: {len(tool_calls)}")
    for tc in tool_calls:
        print(f"     - {tc['name']}({tc['args']})")
    print(f"     Latency: {latency_ms}ms")

    # Validate that at least one expected tool was called
    called_names = {tc["name"] for tc in tool_calls}
    if not called_names.intersection(set(expected_tools)):
        print(f"  ⚠️  Warning: Expected one of {expected_tools}, got {list(called_names)}")

    return True


async def main():
    print("=" * 70)
    print("🧪 LLM PROVIDER TOOL-CALLING TEST")
    print("=" * 70)

    providers = _create_providers()
    if not providers:
        print("❌ No providers available. Check your API keys.")
        return

    results = {}

    for provider_name, model_name, llm in providers:
        print(f"\n{'─' * 70}")
        print(f"🔧 Provider: {provider_name}")
        print(f"   Model:    {model_name}")
        print(f"{'─' * 70}")

        provider_results = []
        for prompt, expected_tools in TEST_PROMPTS:
            print(f"\n  📝 Prompt: \"{prompt}\"")
            success = await test_provider(provider_name, model_name, llm, prompt, expected_tools)
            provider_results.append(success)

        results[provider_name] = provider_results

    # Summary
    print(f"\n{'=' * 70}")
    print("📊 SUMMARY")
    print(f"{'=' * 70}")
    print(f"{'Provider':<12} {'Model':<35} {'Pass':>4}/{len(TEST_PROMPTS)}")
    print("-" * 70)
    for provider_name, model_name, _ in providers:
        passed = sum(results.get(provider_name, []))
        total = len(results.get(provider_name, []))
        icon = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
        print(f"{icon} {provider_name:<10} {model_name:<35} {passed:>4}/{total}")
    print("=" * 70)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
