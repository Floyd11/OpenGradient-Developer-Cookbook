"""
boilerplates/digital-twins-tracker/tracker.py

Digital Twin share price tracker and buyer for Twin.fun (OpenGradient's
Digital Twins platform). Combines on-chain price data with OpenGradient
TEE-verified AI commentary.

What are Digital Twins?
  Twin.fun tokenizes AI personas as shares on a bonding curve contract.
  Each "twin" is a unique AI identity whose shares can be bought/sold.
  Price is determined by a bonding curve: more holders → higher price.

This boilerplate:
  1. Reads current buy/sell price from the DigitalTwinSharesV1 contract
  2. Checks your holdings for a given twin ID
  3. Generates AI price commentary via OpenGradient TEE-verified LLM
  4. Optionally executes buy/sell transactions

Contract: DigitalTwinSharesV1 (Base Sepolia)
Address : 0x065fb766051c9a212218c9D5e8a9B83fb555C17c

Run:
    python tracker.py                    # Read-only price check
    python tracker.py --buy 1            # Buy 1 share (uses real ETH!)
    python tracker.py --twin <twin_id>   # Check a specific twin
"""

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dataclasses import dataclass

import opengradient as og
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3
from web3.exceptions import ContractLogicError

from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DIGITAL_TWIN_SHARES_CONTRACT: str = "0x065fb766051c9a212218c9D5e8a9B83fb555C17c"
RPC_URL: str = os.getenv("RPC_URL", "https://sepolia.base.org")
CHAIN_ID: int = int(os.getenv("CHAIN_ID", "84532"))
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5

# Sample twin ID for testing — find more at https://twin.fun
DEFAULT_TWIN_ID: str = os.getenv("SAMPLE_TWIN_ID", "85f4f72079114bfcac1003134e5424f4")

# Minimal ABI — only the functions we need
DIGITAL_TWIN_ABI: list[dict] = [
    {
        "inputs": [{"name": "twinId", "type": "bytes16"}, {"name": "amount", "type": "uint256"}],
        "name": "getBuyPrice",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "twinId", "type": "bytes16"}, {"name": "amount", "type": "uint256"}],
        "name": "getBuyPriceAfterFee",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "twinId", "type": "bytes16"}, {"name": "amount", "type": "uint256"}],
        "name": "getSellPriceAfterFee",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "protocolFeePercent",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "subjectFeePercent",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "twinId", "type": "bytes16"}, {"name": "holder", "type": "address"}],
        "name": "sharesBalance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "twinId", "type": "bytes16"}, {"name": "amount", "type": "uint256"}],
        "name": "buyShares",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"name": "twinId", "type": "bytes16"}, {"name": "amount", "type": "uint256"}],
        "name": "sellShares",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


@dataclass
class PriceData:
    """Price information for a digital twin."""
    twin_id: str
    buy_price_eth: float
    sell_proceeds_eth: float
    protocol_fee_eth: float
    subject_fee_eth: float
    total_buy_cost_eth: float
    holdings: int
    # Raw integer wei values — use these for transactions to avoid float precision loss
    total_buy_cost_wei: int = 0


# ---------------------------------------------------------------------------
# DigitalTwinsTracker
# ---------------------------------------------------------------------------
class DigitalTwinsTracker:
    """
    Track and trade Digital Twin shares on Twin.fun.

    Combines:
      - On-chain price data (bonding curve contract)
      - AI commentary via OpenGradient TEE-verified LLM
      - Buy/sell transaction execution
    """

    def __init__(self) -> None:
        private_key = os.getenv("OG_PRIVATE_KEY")
        if not private_key:
            raise ValueError("OG_PRIVATE_KEY not set in .env")

        self._private_key = private_key
        self._wallet_address = Account.from_key(private_key).address
        self._w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self._contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(DIGITAL_TWIN_SHARES_CONTRACT),
            abi=DIGITAL_TWIN_ABI,
        )
        self._llm = get_llm()
        self._approved = False

        if not self._w3.is_connected():
            raise ConnectionError(f"Cannot connect to RPC: {RPC_URL}")
        logger.info(f"✅ Connected to Base Sepolia | Wallet: {self._wallet_address}")

    @staticmethod
    def _parse_twin_id(twin_id_str: str) -> bytes:
        """Convert a hex string twin ID to bytes16."""
        clean = twin_id_str.replace("0x", "").replace("-", "")
        if len(clean) != 32:
            raise ValueError(
                f"Twin ID must be 32 hex chars (16 bytes), got {len(clean)}: {clean}"
            )
        return bytes.fromhex(clean)

    def _ensure_llm_approval(self) -> None:
        if not self._approved:
            try:
                approval = self._llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
                if approval.tx_hash:
                    logger.info(f"💰 Permit2 tx: {BASESCAN_TX_URL}{approval.tx_hash}")
                self._approved = True
            except Exception as e:
                raise RuntimeError(
                    f"Permit2 OPG approval failed: {e}\n"
                    f"Check your OPG balance at: https://faucet.opengradient.ai"
                ) from e

    def get_buy_price(self, twin_id: str, amount: int = 1) -> PriceData:
        """
        Get current buy price breakdown for a twin.

        Price formula (bonding curve):
          base_price  = getBuyPrice(twinId, amount)
          protocol_fee = base_price * protocolFeePercent / 1e18
          subject_fee  = base_price * subjectFeePercent / 1e18
          total_cost   = base_price + protocol_fee + subject_fee

        You MUST send exactly `total_cost` as msg.value when calling buyShares.

        Args:
            twin_id: Hex string twin ID (32 chars, no 0x prefix)
            amount: Number of shares to price

        Returns:
            PriceData with all fee breakdowns in ETH
        """
        twin_bytes = self._parse_twin_id(twin_id)

        try:
            price_wei: int = self._contract.functions.getBuyPrice(twin_bytes, amount).call()
            fee_p: int = self._contract.functions.protocolFeePercent().call()
            fee_s: int = self._contract.functions.subjectFeePercent().call()
            sell_wei: int = self._contract.functions.getSellPriceAfterFee(twin_bytes, amount).call()
            holdings: int = self._contract.functions.sharesBalance(
                twin_bytes,
                Web3.to_checksum_address(self._wallet_address),
            ).call()
        except ContractLogicError as e:
            raise RuntimeError(f"Contract call failed: {e}")

        protocol_fee_wei = (price_wei * fee_p) // (10 ** 18)
        subject_fee_wei = (price_wei * fee_s) // (10 ** 18)
        total_cost_wei = price_wei + protocol_fee_wei + subject_fee_wei

        def to_eth(wei: int) -> float:
            return float(Web3.from_wei(wei, "ether"))

        return PriceData(
            twin_id=twin_id,
            buy_price_eth=to_eth(price_wei),
            sell_proceeds_eth=to_eth(sell_wei),
            protocol_fee_eth=to_eth(protocol_fee_wei),
            subject_fee_eth=to_eth(subject_fee_wei),
            total_buy_cost_eth=to_eth(total_cost_wei),
            holdings=holdings,
            total_buy_cost_wei=total_cost_wei,  # exact integer — use this in transactions
        )

    async def get_ai_commentary(self, price_data: PriceData) -> tuple[str, str]:
        """
        Generate TEE-verified AI commentary on a twin's price data.

        This is the unique value-add of this boilerplate: combining
        on-chain price data with verifiable AI analysis. The payment_hash
        proves the commentary was generated from the exact price data shown.

        Args:
            price_data: PriceData from get_buy_price()

        Returns:
            Tuple of (commentary_text, payment_hash)
        """
        self._ensure_llm_approval()

        prompt = (
            f"You are a Digital Twin market analyst on Twin.fun (OpenGradient platform).\n\n"
            f"Analyze this Digital Twin share:\n"
            f"  Twin ID          : {price_data.twin_id}\n"
            f"  Buy Price        : {price_data.buy_price_eth:.6f} ETH\n"
            f"  Total Buy Cost   : {price_data.total_buy_cost_eth:.6f} ETH (incl. fees)\n"
            f"  Sell Proceeds    : {price_data.sell_proceeds_eth:.6f} ETH\n"
            f"  Protocol Fee     : {price_data.protocol_fee_eth:.6f} ETH\n"
            f"  Subject Fee      : {price_data.subject_fee_eth:.6f} ETH\n"
            f"  Your Holdings    : {price_data.holdings} shares\n\n"
            f"Provide:\n"
            f"1. Price spread analysis (buy vs sell)\n"
            f"2. Fee impact assessment\n"
            f"3. One-sentence market sentiment\n\n"
            f"Be concise (3-4 sentences total)."
        )

        result = await self._llm.completion(
            model=DEFAULT_MODEL,
            prompt=prompt,
            max_tokens=200,
            temperature=0.3,
        )
        return result.completion_output, result.payment_hash

    def buy_shares(self, twin_id: str, amount: int = 1) -> str:
        """
        Execute a buyShares transaction.

        ⚠️  This sends a REAL transaction on Base Sepolia.
        You need ETH in your wallet to pay the price + fees.

        Args:
            twin_id: Twin ID hex string
            amount: Number of shares to buy (start with 1)

        Returns:
            Transaction hash as hex string
        """
        twin_bytes = self._parse_twin_id(twin_id)
        price_data = self.get_buy_price(twin_id, amount)

        # Use raw integer wei — avoids float→wei round-trip precision loss
        value_wei = price_data.total_buy_cost_wei

        # Add 2% buffer for price movement between estimate and execution
        value_with_buffer = int(value_wei * 1.02)

        nonce = self._w3.eth.get_transaction_count(
            Web3.to_checksum_address(self._wallet_address)
        )

        tx = self._contract.functions.buyShares(twin_bytes, amount).build_transaction({
            "from": Web3.to_checksum_address(self._wallet_address),
            "value": value_with_buffer,
            "gas": 250000,
            "gasPrice": self._w3.eth.gas_price,
            "nonce": nonce,
            "chainId": CHAIN_ID,
        })

        signed = self._w3.eth.account.sign_transaction(tx, private_key=self._private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def sell_shares(self, twin_id: str, amount: int = 1) -> str:
        """
        Execute a sellShares transaction.

        Args:
            twin_id: Twin ID hex string
            amount: Number of shares to sell

        Returns:
            Transaction hash as hex string
        """
        twin_bytes = self._parse_twin_id(twin_id)
        nonce = self._w3.eth.get_transaction_count(
            Web3.to_checksum_address(self._wallet_address)
        )

        tx = self._contract.functions.sellShares(twin_bytes, amount).build_transaction({
            "from": Web3.to_checksum_address(self._wallet_address),
            "gas": 250000,
            "gasPrice": self._w3.eth.gas_price,
            "nonce": nonce,
            "chainId": CHAIN_ID,
        })

        signed = self._w3.eth.account.sign_transaction(tx, private_key=self._private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(twin_id: str, buy_amount: int = 0, sell_amount: int = 0) -> None:
    tracker = DigitalTwinsTracker()

    print("\n" + "=" * 60)
    print("👥 Digital Twin Tracker — Twin.fun (Base Sepolia)")
    print("=" * 60)
    print(f"  Twin ID  : {twin_id}")
    print(f"  Wallet   : {tracker._wallet_address}")
    print(f"  Contract : {DIGITAL_TWIN_SHARES_CONTRACT}")
    print("=" * 60)

    # 1. Fetch price data
    print("\n📊 Fetching price data from bonding curve...")
    try:
        price_data = tracker.get_buy_price(twin_id, amount=1)
    except Exception as e:
        print(f"❌ Failed to fetch price: {e}")
        print("   Make sure the twin ID is valid and the contract is deployed.")
        return

    print(f"\n  Buy Price (base)  : {price_data.buy_price_eth:.6f} ETH")
    print(f"  Protocol Fee      : {price_data.protocol_fee_eth:.6f} ETH")
    print(f"  Subject Fee       : {price_data.subject_fee_eth:.6f} ETH")
    print(f"  ─────────────────────────────────────")
    print(f"  Total Buy Cost    : {price_data.total_buy_cost_eth:.6f} ETH")
    print(f"  Sell Proceeds     : {price_data.sell_proceeds_eth:.6f} ETH")
    print(f"  Price Spread      : {(price_data.total_buy_cost_eth - price_data.sell_proceeds_eth):.6f} ETH")
    print(f"  Your Holdings     : {price_data.holdings} shares")

    # 2. AI Commentary (verifiable)
    print("\n🤖 Generating AI commentary (TEE-verified)...")
    try:
        commentary, payment_hash = await tracker.get_ai_commentary(price_data)
        print(f"\n  Commentary: {commentary}")
        print(f"\n  💰 Payment Hash : {payment_hash}")
        print(f"  🔗 Verify proof : {BASESCAN_TX_URL}{payment_hash}")
    except Exception as e:
        print(f"⚠️  AI commentary failed: {e}")

    # 3. Execute buy (if requested)
    if buy_amount > 0:
        print(f"\n💸 Buying {buy_amount} share(s)...")
        print(f"   Cost: ~{price_data.total_buy_cost_eth * buy_amount:.6f} ETH")
        confirm = input("   Confirm purchase? [y/N]: ").strip().lower()
        if confirm == "y":
            try:
                tx_hash = tracker.buy_shares(twin_id, buy_amount)
                print(f"   ✅ Buy tx submitted: {BASESCAN_TX_URL}{tx_hash}")
            except Exception as e:
                print(f"   ❌ Buy failed: {e}")
        else:
            print("   Cancelled.")

    # 4. Execute sell (if requested)
    if sell_amount > 0:
        if price_data.holdings < sell_amount:
            print(f"\n❌ Cannot sell {sell_amount} shares — you only hold {price_data.holdings}")
        else:
            print(f"\n💰 Selling {sell_amount} share(s)...")
            confirm = input("   Confirm sale? [y/N]: ").strip().lower()
            if confirm == "y":
                try:
                    tx_hash = tracker.sell_shares(twin_id, sell_amount)
                    print(f"   ✅ Sell tx submitted: {BASESCAN_TX_URL}{tx_hash}")
                except Exception as e:
                    print(f"   ❌ Sell failed: {e}")
            else:
                print("   Cancelled.")

    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Digital Twin share tracker")
    parser.add_argument(
        "--twin",
        default=DEFAULT_TWIN_ID,
        help="Twin ID (32-char hex, no 0x prefix)",
    )
    parser.add_argument(
        "--buy",
        type=int,
        default=0,
        help="Number of shares to buy (use with caution — costs real ETH)",
    )
    parser.add_argument(
        "--sell",
        type=int,
        default=0,
        help="Number of shares to sell",
    )
    args = parser.parse_args()
    asyncio.run(main(twin_id=args.twin, buy_amount=args.buy, sell_amount=args.sell))
