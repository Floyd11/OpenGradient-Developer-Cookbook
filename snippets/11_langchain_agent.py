"""
snippets/11_langchain_agent.py — LangChain Agent with OpenGradient Verifiable LLM

Demonstrates using OpenGradient's TEE-verified LLM as the reasoning backbone
of a LangGraph ReAct agent via the native og.agents.langchain_adapter() (SDK 0.9.x+).

Key Insight:
  og.agents.langchain_adapter() returns a fully LangChain-compatible BaseChatModel
  backed by OpenGradient's TEE inference. Every call produces a transaction_hash
  (and backwards-compatible payment_hash) — a cryptographic proof that the
  reasoning happened inside a Trusted Execution Environment.

Architecture (SDK 0.9.x+):
  og.agents.langchain_adapter()        ←─ returns OpenGradientChatModel
      ↓
  LangGraph create_react_agent          ←─ standard ReAct loop
      ↓
  Tools: [get_weather (stub), ml_inference (real og.Alpha call)]

Note: For a production agent also equipped with on-chain transaction
capabilities, combine this pattern with Coinbase AgentKit (cdp-agentkit),
as used in the official og-agent-starter.

Run:
    python snippets/11_langchain_agent.py

Requirements (in addition to main requirements.txt):
    pip install langgraph langchain-core
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

import opengradient as og
from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0

# Demo ML model CID on OpenGradient's alpha testnet
DEMO_MODEL_CID: str = "QmbUqS93oc4JTLMHwpVxsE39mhNxy6hpf6Py3r9oANr8aZ"

# ---------------------------------------------------------------------------
# Try to import LangGraph (required for create_react_agent)
# ---------------------------------------------------------------------------
try:
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning(
        "LangGraph not installed. Run: pip install langgraph langchain-core\n"
        "Falling back to direct og.LLM call."
    )


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def _get_weather(city: str) -> str:
    """
    Stub weather tool. Replace with a real API (e.g. OpenWeatherMap, Tavily).

    TODO: Real implementation:
      from langchain_community.tools.tavily_search import TavilySearchResults
    """
    logger.info(f"🌤️  get_weather called with: {city}")
    return (
        f"[Mock] Current weather in {city}: 72°F, Partly cloudy, Humidity: 58%. "
        f"(Replace with real weather API in production)"
    )


def _ml_inference(data: str) -> str:
    """
    Real OpenGradient ML inference tool (alpha testnet only).
    Parses comma-separated floats and runs them through the demo model.
    Example input: "1.0,2.0,3.0"

    ⚠️  NOTE: og.Alpha inference is ALPHA TESTNET ONLY.
    """
    logger.info(f"⚗️  ml_inference called with: {data}")
    try:
        private_key = os.getenv("OG_PRIVATE_KEY", "")
        if not private_key:
            return "Error: OG_PRIVATE_KEY not set."
        alpha = og.Alpha(private_key=private_key)
        values = [float(x.strip()) for x in data.split(",") if x.strip()]
        if not values:
            return "Error: provide comma-separated floats, e.g. '1.0,2.0,3.0'"
        result = alpha.infer(
            model_cid=DEMO_MODEL_CID,
            model_input={"num_input1": values[:3]},
            inference_mode=og.InferenceMode.VANILLA,
        )
        # Support both field names across SDK versions
        tx_hash = (
            getattr(result, "transaction_hash", None)
            or getattr(result, "payment_hash", "N/A")
        )
        return (
            f"ML inference result: {result.model_output} "
            f"(verified on-chain: tx={tx_hash})"
        )
    except Exception as e:
        return f"ML inference unavailable: {e} (alpha testnet — try get_weather instead)"


# ---------------------------------------------------------------------------
# Agent entry point
# ---------------------------------------------------------------------------
def build_and_run_agent(task: str) -> None:
    """
    Build a LangGraph ReAct agent backed by OpenGradient's verifiable LLM.

    Uses og.agents.langchain_adapter() (SDK 0.9.x+) for native integration.
    Falls back to direct og.LLM call if LangGraph is not installed.
    """
    if not LANGGRAPH_AVAILABLE:
        print("❌ LangGraph not installed.")
        print("   pip install langgraph langchain-core")
        print("\nFalling back to direct og.LLM call...")
        _run_direct_fallback(task)
        return

    print("\n" + "=" * 65)
    print("🤖 LangGraph Agent — Powered by OpenGradient Verifiable LLM")
    print("=" * 65)
    print(f"📋 Task  : {task}")
    print(f"🧠 Model : {DEFAULT_MODEL.value} (TEE-verified via og.agents.langchain_adapter)")
    print("=" * 65)

    # --- Initialize via og.agents.langchain_adapter (SDK 0.9.x+) ---
    # Returns a fully LangChain-compatible BaseChatModel (OpenGradientChatModel)
    # backed by OpenGradient's TEE inference.
    logger.info("Initializing og.agents.langchain_adapter...")
    try:
        llm = og.agents.langchain_adapter(
            private_key=os.getenv("OG_PRIVATE_KEY"),
            model_cid=DEFAULT_MODEL,
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize langchain_adapter: {e}")
        raise

    # --- Ensure Permit2 OPG allowance ---
    # Must call this once per session before LLM inference.
    logger.info("Checking Permit2 $OPG allowance...")
    try:
        raw_llm = og.LLM(private_key=os.getenv("OG_PRIVATE_KEY"))
        approval = raw_llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
        if approval.tx_hash:
            logger.info(f"💰 Permit2 tx: {BASESCAN_TX_URL}{approval.tx_hash}")
        else:
            logger.info("💰 Permit2 allowance already sufficient")
    except Exception as e:
        logger.warning(f"⚠️  Permit2 check failed (continuing): {e}")

    # --- Define tools using @tool decorator (LangChain convention) ---
    @tool
    def get_weather(city: str) -> str:
        """Get the current weather for a city. Input: city name as a string."""
        return _get_weather(city)

    @tool
    def ml_inference(data: str) -> str:
        """
        Run ML model inference on numerical data using OpenGradient.
        Input: comma-separated float values e.g. '1.0,2.0,3.0'.
        Returns the model output and a verifiable transaction hash.
        """
        return _ml_inference(data)

    tools = [get_weather, ml_inference]

    # --- Build LangGraph ReAct agent ---
    # create_react_agent wraps the LLM with a standard Thought/Action/Observation loop.
    agent = create_react_agent(llm, tools)

    print(f"\n🔄 Running agent on task: {task}\n")
    try:
        result = agent.invoke({
            "messages": [("user", task)]
        })
        final_message = result["messages"][-1]
        final_answer = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )
        print(f"✅ Final Answer:\n{final_answer}")
    except Exception as e:
        logger.error(f"❌ Agent execution failed: {e}")
        raise

    print("\n" + "=" * 65)
    print("ℹ️  Every reasoning step above was TEE-verified on Base Sepolia.")
    print("   transaction_hash on each call proves the exact model and inputs used.")
    print("=" * 65)


def _run_direct_fallback(task: str) -> None:
    """
    Fallback: run the task directly via og.LLM without LangGraph.
    Used when langgraph / langchain-core is not installed.
    """
    llm = get_llm()

    async def _run() -> None:
        approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
        if approval.tx_hash:
            logger.info(f"💰 Permit2 tx: {BASESCAN_TX_URL}{approval.tx_hash}")
        result = await llm.chat(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": task}],
            max_tokens=500,
            temperature=0.0,
        )
        answer = result.chat_output.get("content", "")
        tx = result.transaction_hash or result.payment_hash
        print(f"\n✅ Direct OG LLM Answer:\n{answer}")
        print(f"\n💰 Payment proof: {BASESCAN_TX_URL}{tx}")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    SAMPLE_TASK = (
        "What's the weather like in San Francisco? "
        "Also summarize in 2 sentences why verifiable AI matters for Web3."
    )
    build_and_run_agent(SAMPLE_TASK)
