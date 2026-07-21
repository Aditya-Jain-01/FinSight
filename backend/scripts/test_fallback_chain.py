"""Test the LLM fallback chain logic (Gemini -> Groq -> NVIDIA).

Usage:
    cd backend
    python -m scripts.test_fallback_chain

This script artificially induces a failure in Gemini (and Groq, optionally)
to ensure the LangChain with_fallbacks() routing works correctly and that
tools are properly bound at every step of the chain.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from app.agent.llm_factory import get_llm_with_fallbacks, extract_provider_metadata
from app.agent.tools.registry import TOOLS
from app.agent.nodes.planner import PLANNER_SYSTEM_PROMPT
from app.config import settings

# A prompt that reliably triggers tool usage
TEST_PROMPT = "What is the P/E ratio and market cap of Apple and Microsoft?"


class BrokenLLM(BaseChatModel):
    """A mock LLM that always raises an exception (simulating a 429 or 500 error)."""

    name: str

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError(f"Simulated failure in {self.name}!")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        print(f"    [!] Simulating crash in {self.name}...")
        raise RuntimeError(f"Simulated failure in {self.name}!")

    @property
    def _llm_type(self) -> str:
        return "broken-mock"

    def bind_tools(self, tools, **kwargs):
        # LangChain fallback logic checks if the fallback supports the same interfaces.
        # We just return self here so it doesn't crash during the bind phase.
        return self


async def test_fallback(scenario_name: str, chain: BaseChatModel):
    print(f"\n{'─' * 70}")
    print(f"🧪 Scenario: {scenario_name}")
    print(f"{'─' * 70}")

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=TEST_PROMPT),
    ]

    try:
        response = await chain.ainvoke(messages)
    except Exception as e:
        print(f"  ❌ FAILED: Chain completely threw an exception: {e}")
        return False

    meta = extract_provider_metadata(response)
    tool_calls = getattr(response, "tool_calls", None) or []

    print(f"  ✅ Chain succeeded.")
    print(f"     Provider used:  {meta['provider']} (Model: {meta['model']})")
    print(f"     Fallback triggered: {meta['fallback_used']}")
    print(f"     Tool calls: {len(tool_calls)}")
    for tc in tool_calls:
        print(f"       - {tc['name']}")

    if not tool_calls:
        print("  ⚠️  WARNING: Response succeeded but no tools were called. Tool binding may have been lost in the fallback.")
        return False

    return True


async def main():
    print("=" * 70)
    print("🔄 LLM FALLBACK CHAIN TEST")
    print("=" * 70)

    # 1. Real chain (should use Gemini)
    real_chain = get_llm_with_fallbacks(tools=TOOLS, temperature=0)
    await test_fallback("Normal operation (Should use Gemini)", real_chain)

    # 2. Simulated Gemini failure (should fallback to Groq)
    if settings.groq_api_key:
        broken_gemini = BrokenLLM(name="Gemini")
        # We have to re-create Groq and NVIDIA because the factory builds them fresh
        from app.agent.llm_factory import _create_groq, _create_nvidia
        groq = _create_groq(0).bind_tools(TOOLS)
        
        fallbacks = [groq]
        if settings.nvidia_api_key:
            nvidia = _create_nvidia(0).bind_tools(TOOLS)
            fallbacks.append(nvidia)
            
        simulated_chain_1 = broken_gemini.with_fallbacks(fallbacks)
        await test_fallback("Gemini failure (Should fallback to Groq)", simulated_chain_1)
    else:
        print("\n⚠️  GROQ_API_KEY not set — skipping Gemini failure scenario.")

    # 3. Simulated Gemini + Groq failure (should fallback to NVIDIA)
    if settings.groq_api_key and settings.nvidia_api_key:
        broken_gemini = BrokenLLM(name="Gemini")
        broken_groq = BrokenLLM(name="Groq")
        
        from app.agent.llm_factory import _create_nvidia
        nvidia = _create_nvidia(0).bind_tools(TOOLS)
        
        simulated_chain_2 = broken_gemini.with_fallbacks([broken_groq, nvidia])
        await test_fallback("Gemini & Groq failure (Should fallback to NVIDIA)", simulated_chain_2)
    else:
        print("\n⚠️  NVIDIA_API_KEY (or Groq) not set — skipping double-failure scenario.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
