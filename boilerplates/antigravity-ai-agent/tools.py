"""
boilerplates/antigravity-ai-agent/tools.py

Tool definitions for the VerifiableAgent. Each tool is a callable that the
agent can use during its execution loop.

In this boilerplate:
  - search_web()    → stub (replace with Tavily / SerpAPI / Brave)
  - analyze_data()  → real OpenGradient LLM call (verifiable)
  - format_report() → pure Python, no AI needed
"""

import logging
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import opengradient as og
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("og.agent.tools")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"


def search_web(query: str) -> str:
    """
    Search the web for information about a given query.

    Args:
        query: Natural language search query

    Returns:
        Search result as a string

    TODO: Replace this stub with a real implementation:
        Option A (Tavily — best for agents):
            from tavily import TavilyClient
            client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
            return client.search(query)["results"][0]["content"]

        Option B (SerpAPI):
            from langchain_community.utilities import SerpAPIWrapper
            search = SerpAPIWrapper(serpapi_api_key=os.getenv("SERPAPI_KEY"))
            return search.run(query)

        Option C (Brave Search API):
            import httpx
            resp = httpx.get("https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": os.getenv("BRAVE_API_KEY")},
                params={"q": query})
            return resp.json()["web"]["results"][0]["description"]
    """
    logger.info(f"🔍 search_web('{query[:60]}...')")

    # Mock result — replace with real search
    mock_results = {
        "verifiable ai": (
            "Verifiable AI refers to AI systems where the computation can be "
            "cryptographically proven. OpenGradient uses TEE (Trusted Execution "
            "Environments) to provide hardware-level attestation for LLM inference, "
            "ensuring that specific prompts were processed securely. Key use cases "
            "include DeFi protocols, healthcare, and compliance-heavy industries."
        ),
        "defi smart contract security": (
            "DeFi smart contract vulnerabilities cost over $1.8B in 2023. Common "
            "attack vectors include reentrancy, flash loan attacks, and oracle "
            "manipulation. TEE-verified AI can provide auditable smart contract "
            "analysis with cryptographic proof of the analysis criteria used."
        ),
        "opengradient": (
            "OpenGradient is a research lab building the frontier of AI and "
            "blockchain computing. Products include: x402 Gateway (TEE-verified "
            "LLM inference), Model Hub (decentralized ONNX model storage on Walrus), "
            "MemSync (persistent AI memory), and Digital Twins (tokenized AI personas)."
        ),
    }

    # Find the best matching mock result
    query_lower = query.lower()
    for key, result in mock_results.items():
        if any(word in query_lower for word in key.split()):
            return result

    return (
        f"[Mock search result for '{query}']: "
        f"This is a placeholder. Replace search_web() with a real search API. "
        f"See TODO comments in tools.py for implementation options."
    )


async def analyze_data(data: str, question: str = "What are the key insights?") -> tuple[str, str]:
    """
    Analyze data using OpenGradient's verifiable LLM.

    This tool makes a REAL TEE-verified inference call. The returned
    payment_hash is cryptographic proof of the analysis.

    Args:
        data: Raw data or text to analyze
        question: What to analyze for

    Returns:
        Tuple of (analysis_text, payment_hash)
    """
    logger.info(f"⚗️  analyze_data — question: '{question[:60]}'")

    try:
        from utils.client import get_llm
        llm = get_llm()

        prompt = (
            f"Analyze the following data and answer this question: {question}\n\n"
            f"Data:\n{data}\n\n"
            f"Provide a concise, structured analysis."
        )

        result = await llm.completion(
            model=DEFAULT_MODEL,
            prompt=prompt,
            max_tokens=400,
            temperature=0.0,
        )
        logger.info(f"✅ Analysis complete — proof: {result.payment_hash[:20]}...")
        return result.completion_output, result.payment_hash

    except Exception as e:
        logger.error(f"❌ analyze_data failed: {e}")
        return f"Analysis failed: {e}", ""


def format_report(
    findings: list[str],
    title: str = "Agent Research Report",
    payment_hashes: list[str] | None = None,
) -> str:
    """
    Format a list of findings into a structured report string.

    Args:
        findings: List of finding strings from agent steps
        title: Report title
        payment_hashes: Optional list of tx hashes for the proof trail

    Returns:
        Formatted report as a multi-line string
    """
    separator = "=" * 60
    lines = [
        separator,
        f"📋 {title}",
        separator,
        "",
    ]

    for i, finding in enumerate(findings, 1):
        lines.append(f"  {i}. {finding}")
        lines.append("")

    if payment_hashes:
        lines.extend([
            separator,
            "🔐 Cryptographic Proof Trail",
            separator,
        ])
        for i, ph in enumerate(payment_hashes, 1):
            if ph:
                lines.append(f"  Step {i}: {BASESCAN_TX_URL}{ph}")

    lines.extend(["", separator])
    return "\n".join(lines)
