"""
snippets/01_llm_completion_basic.py — Simple Verifiable LLM Completion

Demonstrates the "Hello World" of OpenGradient: sending a text prompt to a
TEE-verified LLM via the x402 Gateway and receiving a cryptographic proof
(payment_hash) that the inference happened inside a Trusted Execution Environment.

When to use this pattern:
  - You need a single, non-conversational text completion
  - You want the simplest possible integration point
  - Use llm.chat() instead if you need multi-turn conversations or tool calling

Run:
    python snippets/01_llm_completion_basic.py
"""

import asyncio
import logging
import os
import sys

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import opengradient as og
from dotenv import load_dotenv

from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Default model — change to any supported TEE_LLM value below:
#
# OpenAI:    og.TEE_LLM.GPT_5 | GPT_5_MINI | GPT_4_1_2025_04_14 | O4_MINI
# Anthropic: og.TEE_LLM.CLAUDE_OPUS_4_6 | CLAUDE_SONNET_4_6 | CLAUDE_HAIKU_4_5
# Google:    og.TEE_LLM.GEMINI_3_PRO | GEMINI_2_5_PRO | GEMINI_2_5_FLASH
# xAI:       og.TEE_LLM.GROK_4 | GROK_4_FAST
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
MAX_TOKENS: int = 150
TEMPERATURE: float = 0.0
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0

SAMPLE_PROMPT: str = (
    "Explain in one sentence why verifiable AI inference matters for DeFi protocols."
)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def run_completion() -> None:
    """Run a single verifiable LLM completion and print the result."""
    llm = get_llm()

    # Step 1: Ensure Permit2 allowance for $OPG payments.
    # This is a no-op if the allowance is already sufficient.
    # Call once at app startup — not before every request.
    logger.info("Checking Permit2 $OPG allowance...")
    try:
        approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
        if approval.tx_hash:
            logger.info(f"💰 Permit2 approval tx: {BASESCAN_TX_URL}{approval.tx_hash}")
        else:
            logger.info("💰 Permit2 allowance already sufficient — no transaction needed")
    except Exception as e:
        logger.error(f"❌ Permit2 approval failed: {e}")
        raise

    # Step 2: Run the verifiable completion
    logger.info(f"🤖 Sending prompt to {DEFAULT_MODEL.value}...")
    try:
        result = await llm.completion(
            model=DEFAULT_MODEL,
            prompt=SAMPLE_PROMPT,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
    except ConnectionError as e:
        logger.error(f"❌ Network error during inference: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Inference failed: {e}")
        raise

    # Step 3: Print results
    print("\n" + "=" * 60)
    print("✅ Verifiable LLM Completion — Result")
    print("=" * 60)
    print(f"🤖 Model      : {DEFAULT_MODEL.value}")
    print(f"📝 Prompt     : {SAMPLE_PROMPT}")
    print(f"\n💬 Response:\n  {result.completion_output}")
    print(f"\n💰 Payment Hash : {result.payment_hash}")
    print(f"🔗 Verify on-chain: {BASESCAN_TX_URL}{result.payment_hash}")
    print("=" * 60)
    print(
        "\nℹ️  The payment_hash above is your cryptographic proof that this inference\n"
        "   was processed inside a TEE (Trusted Execution Environment).\n"
        "   Anyone can verify this on the OpenGradient block explorer:\n"
        f"   https://explorer.opengradient.ai"
    )


if __name__ == "__main__":
    asyncio.run(run_completion())
