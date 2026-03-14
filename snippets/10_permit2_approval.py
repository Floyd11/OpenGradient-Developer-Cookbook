"""
snippets/10_permit2_approval.py — OPG Permit2 Token Approval

Demonstrates the Permit2 approval flow required before making any LLM
inference calls through the x402 Gateway.

Run:
    python snippets/10_permit2_approval.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0


def run_permit2_approval() -> None:
    """Check and update the Permit2 OPG allowance."""
    llm = get_llm()

    print("\n" + "=" * 60)
    print("🔐 Permit2 OPG Token Approval")
    print("=" * 60)

    try:
        approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
        print(f"  Allowance Before: {approval.allowance_before:.4f} OPG")
        print(f"  Allowance After: {approval.allowance_after:.4f} OPG")
        print(f"  Transaction Hash: {approval.tx_hash or 'None'}")
    except Exception as e:
        print(f"\n❌ Permit2 approval failed: {e}")
        raise


if __name__ == "__main__":
    run_permit2_approval()
