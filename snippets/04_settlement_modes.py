"""
snippets/04_settlement_modes.py — x402 Settlement Mode Comparison

Demonstrates all three x402SettlementMode options. Settlement modes control
how inference data is recorded on the OpenGradient blockchain, offering
different tradeoffs between privacy, cost, and auditability.

Settlement Mode Reference:
┌─────────────────┬─────────┬──────┬──────────────────┬──────────────────────────────┐
│ Mode            │ Privacy │ Cost │ On-Chain Data    │ Best For                     │
├─────────────────┼─────────┼──────┼──────────────────┼──────────────────────────────┤
│ PRIVATE         │ MAX     │ LOW  │ None             │ Sensitive data, healthcare   │
│ INDIVIDUAL_FULL │ MIN     │ HIGH │ Full prompt+resp │ DeFi audits, compliance      │
│ BATCH_HASHED    │ MED     │ MED  │ Hashed (Merkle)  │ High-volume production apps  │
└─────────────────┴─────────┴──────┴──────────────────┴──────────────────────────────┘

When to use each mode:
  PRIVATE         — Patient data, personal info, trade secrets
  INDIVIDUAL_FULL — DeFi agent decisions that must be auditable on-chain,
                    regulatory compliance, "proof of what prompt was used"
  BATCH_HASHED    — Default for most apps; balances cost and auditability;
                    proofs are verifiable via Merkle inclusion, not raw data

Run:
    python snippets/04_settlement_modes.py
"""

import asyncio
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import opengradient as og
from dotenv import load_dotenv

from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0

TEST_PROMPT: str = (
    "In one sentence, what is the key benefit of verifiable AI inference?"
)

MODES_TO_TEST: list[tuple[og.x402SettlementMode, str, str]] = [
    (
        og.x402SettlementMode.PRIVATE,
        "PRIVATE",
        "No on-chain data — maximum privacy, minimum cost",
    ),
    (
        og.x402SettlementMode.INDIVIDUAL_FULL,
        "INDIVIDUAL_FULL",
        "Full prompt+response on-chain — maximum auditability for DeFi/compliance",
    ),
    (
        og.x402SettlementMode.BATCH_HASHED,
        "BATCH_HASHED",
        "Merkle-batched hashes — default, cost-efficient for high-volume apps",
    ),
]


@dataclass
class ModeResult:
    """Result from a single settlement mode inference."""
    mode_name: str
    description: str
    response: str
    payment_hash: str


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def compare_settlement_modes() -> None:
    """Run the same prompt through all three settlement modes and compare."""
    llm = get_llm()

    # Ensure Permit2 allowance
    logger.info("Checking Permit2 $OPG allowance...")
    try:
        approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
        if approval.tx_hash:
            logger.info(f"💰 Permit2 approval tx: {BASESCAN_TX_URL}{approval.tx_hash}")
    except Exception as e:
        logger.error(f"❌ Permit2 approval failed: {e}")
        raise

    messages: list[dict] = [
        {"role": "user", "content": TEST_PROMPT}
    ]

    results: list[ModeResult] = []

    print("\n" + "=" * 70)
    print("⚖️  Settlement Mode Comparison")
    print(f"📝 Prompt: {TEST_PROMPT}")
    print("=" * 70)

    for mode, mode_name, description in MODES_TO_TEST:
        logger.info(f"🔄 Testing settlement mode: {mode_name}...")
        try:
            result = await llm.chat(
                model=DEFAULT_MODEL,
                messages=messages,
                x402_settlement_mode=mode,
                max_tokens=100,
                temperature=0.0,
            )
            response_text = result.chat_output.get("content", "")
            results.append(ModeResult(
                mode_name=mode_name,
                description=description,
                response=response_text,
                payment_hash=result.payment_hash,
            ))
            logger.info(f"✅ {mode_name} — payment_hash: {result.payment_hash[:20]}...")
        except Exception as e:
            logger.error(f"❌ {mode_name} inference failed: {e}")
            raise

    # Print comparison table
    print(f"\n{'Mode':<20} {'Privacy':<8} {'Cost':<6} {'On-Chain Data':<20}")
    print("-" * 60)
    metadata = {
        "PRIVATE":         ("MAX",  "LOW",  "None"),
        "INDIVIDUAL_FULL": ("MIN",  "HIGH", "Full prompt+resp"),
        "BATCH_HASHED":    ("MED",  "MED",  "Hashed (Merkle)"),
    }
    for r in results:
        priv, cost, onchain = metadata[r.mode_name]
        print(f"{r.mode_name:<20} {priv:<8} {cost:<6} {onchain:<20}")

    print("\n" + "=" * 70)
    print("📋 Detailed Results:")
    print("=" * 70)
    for r in results:
        print(f"\n🔷 Mode: {r.mode_name}")
        print(f"   ℹ️  {r.description}")
        print(f"   💬 Response: {r.response[:120]}...")
        print(f"   💰 Payment Hash: {r.payment_hash}")
        print(f"   🔗 {BASESCAN_TX_URL}{r.payment_hash}")

    print("\n" + "=" * 70)
    print("💡 Recommendation:")
    print("   • Default production app    → BATCH_HASHED")
    print("   • DeFi agent / compliance   → INDIVIDUAL_FULL")
    print("   • Healthcare / personal PII → PRIVATE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(compare_settlement_modes())
