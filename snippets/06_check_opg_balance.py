"""
snippets/06_check_opg_balance.py — Wallet Inspector (Base Sepolia)

Checks your testnet wallet's ETH and $OPG token balances on Base Sepolia.
Also shows the current Permit2 allowance for $OPG spending.

Run this script first to verify your wallet is funded before running any
LLM inference snippets.

Requirements:
  - OG_PRIVATE_KEY in .env (the wallet to inspect)
  - RPC_URL in .env (default: https://sepolia.base.org)

Run:
    python snippets/06_check_opg_balance.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError

from utils.client import logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RPC_URL: str = os.getenv("RPC_URL", "https://sepolia.base.org")
CHAIN_ID: int = int(os.getenv("CHAIN_ID", "84532"))
OPG_TOKEN_CONTRACT: str = os.getenv(
    "OPG_TOKEN_CONTRACT",
    "0x240b09731D96979f50B2C649C9CE10FcF9C7987F",
)
FAUCET_URL: str = "https://faucet.opengradient.ai"

# Minimal ERC-20 ABI — only the functions we need
ERC20_ABI: list[dict] = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Uniswap Permit2 contract address (same across all EVM chains)
PERMIT2_ADDRESS: str = "0x000000000022D473030F116dDEE9F6B43aC78BA3"


def get_wallet_address(private_key: str) -> str:
    """Derive the wallet address from a private key."""
    from eth_account import Account
    account = Account.from_key(private_key)
    return account.address


def format_wei(wei_amount: int, decimals: int = 18) -> str:
    """Format a wei integer to a human-readable decimal string."""
    divisor = 10 ** decimals
    whole = wei_amount // divisor
    frac = wei_amount % divisor
    frac_str = str(frac).zfill(decimals)[:4]  # Show 4 decimal places
    return f"{whole}.{frac_str}"


def inspect_wallet() -> None:
    """Inspect the configured wallet's balances on Base Sepolia."""
    # Load private key
    private_key = os.getenv("OG_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "OG_PRIVATE_KEY not set in .env\n"
            "Please configure your testnet wallet private key."
        )

    # Derive wallet address from private key (never hardcode addresses)
    wallet_address = get_wallet_address(private_key)
    checksum_address = Web3.to_checksum_address(wallet_address)

    logger.info(f"Connecting to Base Sepolia RPC: {RPC_URL}")

    # Connect to Base Sepolia
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(
            f"Failed to connect to RPC: {RPC_URL}\n"
            f"Check your internet connection or try a different RPC endpoint."
        )

    connected_chain_id = w3.eth.chain_id
    if connected_chain_id != CHAIN_ID:
        raise ValueError(
            f"Connected to chain {connected_chain_id}, expected {CHAIN_ID} (Base Sepolia)"
        )

    # Initialize OPG token contract
    opg_contract = w3.eth.contract(
        address=Web3.to_checksum_address(OPG_TOKEN_CONTRACT),
        abi=ERC20_ABI,
    )

    # Fetch balances
    logger.info("Fetching balances...")
    try:
        eth_balance_wei: int = w3.eth.get_balance(checksum_address)
        opg_balance_raw: int = opg_contract.functions.balanceOf(checksum_address).call()
        opg_decimals: int = opg_contract.functions.decimals().call()
        opg_symbol: str = opg_contract.functions.symbol().call()
    except ContractLogicError as e:
        logger.error(f"Contract call failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to fetch balances: {e}")
        raise

    # Fetch Permit2 allowance for OPG
    permit2_allowance_raw: int = 0
    try:
        permit2_allowance_raw = opg_contract.functions.allowance(
            checksum_address,
            Web3.to_checksum_address(PERMIT2_ADDRESS),
        ).call()
    except Exception as e:
        logger.warning(f"Could not fetch Permit2 allowance: {e}")

    eth_balance = float(Web3.from_wei(eth_balance_wei, "ether"))
    opg_balance = opg_balance_raw / (10 ** opg_decimals)
    permit2_allowance = permit2_allowance_raw / (10 ** opg_decimals)

    # Determine status
    if opg_balance >= 1.0:
        status = "✅ Ready — wallet has $OPG for inference"
    elif opg_balance > 0:
        status = f"⚠️  Low $OPG — get more at {FAUCET_URL}"
    else:
        status = f"❌ No $OPG — get tokens at {FAUCET_URL}"

    # Print formatted summary
    print("\n" + "=" * 52)
    print("💼 Wallet Inspector — Base Sepolia Testnet")
    print("=" * 52)
    print(f"  Address    : {checksum_address}")
    print(f"  Chain      : Base Sepolia (ID: {CHAIN_ID})")
    print(f"  RPC        : {RPC_URL}")
    print("-" * 52)
    print(f"  ETH        : {eth_balance:.4f} ETH  (for gas fees)")
    print(f"  {opg_symbol:<10} : {opg_balance:.4f} OPG  (for AI inference)")
    print(f"  Permit2    : {permit2_allowance:.4f} OPG  (approved for x402 Gateway)")
    print("-" * 52)
    print(f"  Status     : {status}")
    print("=" * 52)

    if opg_balance == 0:
        print(f"\n🚰 Get test $OPG tokens: {FAUCET_URL}")

    if permit2_allowance < 1.0 and opg_balance > 0:
        print(
            "\n💡 Tip: Your Permit2 allowance is low.\n"
            "   Run: python snippets/10_permit2_approval.py"
        )


if __name__ == "__main__":
    inspect_wallet()
