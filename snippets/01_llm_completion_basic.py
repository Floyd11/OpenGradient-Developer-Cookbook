"""
snippets/01_llm_completion_basic.py — Basic LLM Completion (x402 Gateway)

The simplest possible OpenGradient LLM call.
Sends a single prompt and receives a verifiable completion with a payment_hash
that proves the inference ran inside a Trusted Execution Environment (TEE).

Key concepts demonstrated:
  1. og.LLM initialization (uses OG_PRIVATE_KEY for x402 micropayment auth)
  2. Permit2 allowance approval (one-time per session)
  3. Single-turn completion with og.TEE_LLM model selection
  4. payment_hash / transaction_hash — the on-chain proof of inference

Run:
    python snippets/01_llm_completion_basic.py
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
# Model selection — all available TEE_LLM models as of SDK 0.9.3:
#
# OpenAI:    og.TEE_LLM.GPT_4_1_2025_04_14 | O4_MINI | GPT_5 | GPT_5_MINI | GPT_5_2
# Anthropic: og.TEE_LLM.CLAUDE_SONNET_4_5 | CLAUDE_SONNET_4_6 | CLAUDE_HAIKU_4_5
#                      | CLAUDE_OPUS_4_5 | CLAUDE_OPUS_4_6
# Google:    og.TEE_LLM.GEMINI_2_5_FLASH | GEMINI_2_5_PRO | GEMINI_2_5_FLASH_LITE
#                      | GEMINI_3_PRO | GEMINI_3_FLASH
# xAI:       og.TEE_LLM.GROK_4 | GROK_4_FAST | GROK_4_1_FAST | GROK_4_1_FAST_NON_REASONING
# ---------------------------------------------------------------------------
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5

# Amount of $OPG to approve for Permit2 spending (covers ~5 inference calls)
OPG_APPROVAL_AMOUNT: float = 5.0

# Basescan URL for verifying payment transactions on Base Sepolia
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"


async def run_basic_completion() -> None:
    """Demonstrate a single verifiable LLM completion via OpenGradient."""
    llm = get_llm()

    # Step 1: Approve $OPG spending via Permit2 (only necessary once per session).
    # ensure_opg_approval is idempotent — it checks the current allowance first
    # and only submits an on-chain transaction if the allowance is insufficient.
    logger.info("Checking Permit2 $OPG allowance...")
    approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
    if approval.tx_hash:
        logger.info(f"💰 New Permit2 approval tx: {BASESCAN_TX_URL}{approval.tx_hash}")
    else:
        logger.info("💰 Permit2 allowance already sufficient — skipping")

    # Step 2: Send a single completion prompt.
    prompt = (
        "In one sentence, explain what makes OpenGradient's verifiable AI "
        "inference different from standard cloud LLM APIs."
    )

    logger.info(f"Sending prompt to {DEFAULT_MODEL.value}...")
    result = await llm.completion(
        model=DEFAULT_MODEL,
        prompt=prompt,
        max_tokens=200,
        temperature=0.0,   # Deterministic output for reproducibility
    )

    # Step 3: Display the result and the on-chain proof.
    # transaction_hash is the primary field (SDK 0.9.x+).
    # payment_hash remains available for backwards compatibility.
    tx_hash = result.transaction_hash or result.payment_hash

    print("\n" + "=" * 60)
    print("🧠 OpenGradient Verifiable LLM — Basic Completion")
    print("=" * 60)
    print(f"  Model  : {DEFAULT_MODEL.value}")
    print(f"  Prompt : {prompt}")
    print("-" * 60)
    print(f"  Output : {result.completion_output}")
    print("-" * 60)
    print(f"  🔐 Proof  : {BASESCAN_TX_URL}{tx_hash}")
    print("=" * 60)
    print(
        "\nℹ️  The URL above is the on-chain proof that this exact model "
        "received this exact prompt inside a Trusted Execution Environment."
    )


if __name__ == "__main__":
    asyncio.run(run_basic_completion())
