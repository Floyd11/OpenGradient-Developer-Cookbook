"""
snippets/10_permit2_approval.py — OPG Permit2 Token Approval

Demonstrates the Permit2 approval flow required before making any LLM
inference calls through the x402 Gateway.

What is Permit2?
  Permit2 is Uniswap's universal token approval contract deployed at the same
  address on all EVM chains. It enables "gasless" ERC-20 approvals through
  off-chain signatures, reducing the number of on-chain transactions needed.

  The OpenGradient x402 Gateway uses Permit2 so that:
    1. You approve OPG tokens to the Permit2 contract ONCE (on-chain)
    2. Every subsequent LLM inference payment uses an off-chain Permit2
       signature — no additional approval tx needed per inference

Best Practice:
  - Call ensure_opg_approval() ONCE at app startup
  - If tx_hash is None → allowance already sufficient, no tx was sent
  - If tx_hash is not None → a new approval tx was submitted
  - You don't need to call this before every inference request

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
# How many OPG tokens to approve for Permit2 spending.
# 5.0 OPG is enough for dozens of inference calls.
# Increase this if you expect high-volume usage.
OPG_APPROVAL_AMOUNT: float = 5.0

PERMIT2_CONTRACT: str = "0x000000000022D473030F116dDEE9F6B43aC78BA3"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_permit2_approval() -> None:
    """Check and update the Permit2 OPG allowance."""
    llm = get_llm()

    print("\n" + "=" * 60)
    print("🔐 Permit2 OPG Token Approval")
    print("=" * 60)
    print(f"   Permit2 Contract : {PERMIT2_CONTRACT}")
    print(f"   Approval Amount  : {OPG_APPROVAL_AMOUNT} OPG")
    print()
    print("   This approves OPG tokens for the Permit2 contract,")
    print("   enabling the x402 Gateway to collect payment for each")
    print("   LLM inference call without a new approval tx each time.")
    print("=" * 60)

    logger.info(f"Checking Permit2 allowance for {OPG_APPROVAL_AMOUNT} OPG...")

    try:
        approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
    except Exception as e:
        print(f"\n❌ Permit2 approval failed: {e}")
        print("\nPossible causes:")
        print("  • Insufficient ETH for gas fees")
        print("  • OPG balance too low (get tokens at https://faucet.opengradient.ai)")
        print("  • RPC connection issue")
        raise

    print(f"\n{'Field':<25} {'Value'}")
    print("-" * 55)
    print(f"  {'Allowance Before':<23}: {approval.allowance_before:.4f} OPG")
    print(f"  {'Allowance After':<23}: {approval.allowance_after:.4f} OPG")
    print(f"  {'Transaction Hash':<23}: {approval.tx_hash or 'None (no tx needed)'}")

    if approval.tx_hash:
        print(f"\n✅ New approval transaction submitted!")
        print(f"   💰 Tx Hash : {approval.tx_hash}")
        print(f"   🔗 View    : {BASESCAN_TX_URL}{approval.tx_hash}")
        print(f"\n   Your wallet has approved {approval.allowance_after:.4f} OPG")
        print(f"   for Permit2 spending. You can now run LLM inference.")
    else:
        print(f"\n✅ Allowance already sufficient!")
        print(f"   No on-chain transaction was needed.")
        print(f"   Current allowance: {approval.allowance_after:.4f} OPG")

    print("\n" + "=" * 60)
    print("💡 Tips:")
    print("   • Call ensure_opg_approval() once at app startup")
    print("   • Not needed before every inference call")
    print("   • Increase opg_amount if you run high-volume inference")
    print("   • Get more OPG: https://faucet.opengradient.ai")
    print("=" * 60)

    print("\n📋 Next steps:")
    print("   python snippets/01_llm_completion_basic.py  # Run your first inference")
    print("   python snippets/06_check_opg_balance.py     # Verify your wallet balance")


if __name__ == "__main__":
    run_permit2_approval()
