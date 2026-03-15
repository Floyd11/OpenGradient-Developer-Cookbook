"""
snippets/09_ml_workflow_deploy.py — ML Workflow Deployment & Reading

Demonstrates deploying and consuming automated ML workflows on OpenGradient.
Workflows automatically:
  - Collect live price data from on-chain oracles (e.g., ETH/USD OHLC candles)
  - Execute ML model inference on a schedule
  - Store results on-chain for applications to consume

Official OG Workflow Contracts (pre-deployed, ready to read):
┌─────────────────────────────┬──────────────────────────────────────────────┐
│ Model                       │ Contract Address                             │
├─────────────────────────────┼──────────────────────────────────────────────┤
│ 1hr ETH/USD Volatility      │ 0xD5629A5b95dde11e4B5772B5Ad8a13B933e33845  │
│ 30min SUI/USD Return        │ 0xD85BA71f5701dc4C5BDf9780189Db49C6F3708D2  │
│ 6hr SUI/USD Return          │ 0x3C2E4DbD653Bd30F1333d456480c1b7aB122e946  │
└─────────────────────────────┴──────────────────────────────────────────────┘

⚠️  WARNING: Alpha testnet only — not yet on official testnet.

SDK NOTE: Workflows and ML inference use the standalone og.Alpha class,
NOT og.Client. The correct init is:
    alpha = og.Alpha(private_key=os.getenv("OG_PRIVATE_KEY"))

Then call methods directly on the alpha object:
    alpha.infer(...)
    alpha.new_workflow(...)
    alpha.run_workflow(contract_address)
    alpha.read_workflow_result(contract_address)

Run:
    python snippets/09_ml_workflow_deploy.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import opengradient as og
from opengradient.types import (
    CandleOrder,
    CandleType,
    HistoricalInputQuery,
    SchedulerParams,
)
from dotenv import load_dotenv

from utils.client import logger

load_dotenv()

# ---------------------------------------------------------------------------
# Official OpenGradient ML Workflow Contracts
# ---------------------------------------------------------------------------
OG_WORKFLOWS: dict[str, dict] = {
    "1hr-volatility-ethusdt": {
        "contract": "0xD5629A5b95dde11e4B5772B5Ad8a13B933e33845",
        "model_cid": "QmRhcpDXfYCKsimTmJYrAVM4Bbvck59Zb2onj3MHv9Kw5N",
        "description": "1-hour ETH/USD volatility prediction (std dev of 1min returns)",
        "hub_url": "https://hub.opengradient.ai/models/OpenGradient/og-1hr-volatility-ethusdt",
    },
    "30min-return-suiusdt": {
        "contract": "0xD85BA71f5701dc4C5BDf9780189Db49C6F3708D2",
        "model_cid": "QmY1RjD3s4XPbSeKi5TqMwbxegumenZ49t2q7TrK7Xdga4",
        "description": "30-minute SUI/USD return forecast",
        "hub_url": "https://hub.opengradient.ai/models/OpenGradient/og-30min-return-suiusdt",
    },
    "6h-return-suiusdt": {
        "contract": "0x3C2E4DbD653Bd30F1333d456480c1b7aB122e946",
        "model_cid": "QmP4BeRjycVxfKBkFtwj5xAa7sCWyffMQznNsZnXgYHpFX",
        "description": "6-hour SUI/USD return forecast",
        "hub_url": "https://hub.opengradient.ai/models/OpenGradient/og-6h-return-suiusdt",
    },
}

OG_EXPLORER_URL: str = "https://explorer.opengradient.ai"


def _get_alpha() -> og.Alpha:
    """
    Return an initialized og.Alpha instance for ML inference and workflows.

    Per official docs (docs.opengradient.ai/developers/sdk/ml_inference.html):
    Workflows and ML inference use the STANDALONE og.Alpha class, NOT og.Client.

    Correct init:
        alpha = og.Alpha(private_key="<key>")
        alpha.infer(...)
        alpha.new_workflow(...)
        alpha.run_workflow(contract_address)
        alpha.read_workflow_result(contract_address)
    """
    private_key = os.getenv("OG_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "OG_PRIVATE_KEY not set in .env\n"
            "Get test OPG tokens at: https://faucet.opengradient.ai"
        )
    return og.Alpha(private_key=private_key)


# ---------------------------------------------------------------------------
# Read from existing official workflow
# ---------------------------------------------------------------------------
def read_official_workflow(workflow_key: str = "1hr-volatility-ethusdt") -> None:
    """Read the latest result from an official pre-deployed OG workflow."""
    alpha = _get_alpha()
    workflow = OG_WORKFLOWS[workflow_key]
    contract_address: str = workflow["contract"]

    print(f"\n📡 Reading from official OG workflow: {workflow_key}")
    print(f"   Contract : {contract_address}")
    print(f"   Model    : {workflow['description']}")

    try:
        # Manually trigger a fresh inference with latest oracle data
        logger.info("Running workflow with latest oracle data...")
        alpha.run_workflow(contract_address)
        logger.info("✅ Workflow executed")

        # Read the latest result stored on-chain
        result = alpha.read_workflow_result(contract_address)
        print(f"\n✅ Latest workflow result:")
        print(f"   Output: {result}")
        print(f"   View at: {OG_EXPLORER_URL}")

    except Exception as e:
        logger.error(f"❌ Failed to read workflow: {e}")
        logger.warning("   Alpha testnet may be unreachable. Try again later.")


# ---------------------------------------------------------------------------
# Deploy a new custom workflow
# ---------------------------------------------------------------------------
def deploy_custom_workflow() -> str | None:
    """
    Deploy a new ML workflow that runs on a schedule with live oracle data.

    This example deploys the same ETH volatility model from the official
    workflows, but as a new custom deployment you control.

    Returns:
        The deployed contract address, or None if deployment failed
    """
    alpha = _get_alpha()

    print("\n🚀 Deploying custom ETH volatility workflow...")
    print("   Model: 1-hour ETH/USD volatility (OHLC input)")
    print("   Schedule: every 1 hour for 30 days")

    # Define the data input query — what oracle data the model needs
    input_query = HistoricalInputQuery(
        base="ETH",
        quote="USD",
        total_candles=10,             # Number of historical candles
        candle_duration_in_mins=30,   # 30-minute candles
        order=CandleOrder.ASCENDING,  # Oldest first
        candle_types=[
            CandleType.OPEN,
            CandleType.HIGH,
            CandleType.LOW,
            CandleType.CLOSE,
        ],
    )

    # Define the execution schedule
    scheduler_params = SchedulerParams(
        frequency=3600,       # Run every 3600 seconds (1 hour)
        duration_hours=720,   # Run for 720 hours = 30 days
    )

    model_cid = OG_WORKFLOWS["1hr-volatility-ethusdt"]["model_cid"]

    try:
        contract_address = alpha.new_workflow(
            model_cid=model_cid,
            input_query=input_query,
            input_tensor_name="open_high_low_close",  # Must match model's input name
            scheduler_params=scheduler_params,
        )

        print(f"\n✅ Workflow deployed successfully!")
        print(f"   Contract Address : {contract_address}")
        print(f"   Schedule         : Every 1 hour for 30 days")
        print(f"   Explorer         : {OG_EXPLORER_URL}/address/{contract_address}")
        print(f"\n   To read results later:")
        print(f"   alpha = og.Alpha(private_key=os.getenv('OG_PRIVATE_KEY'))")
        print(f"   result = alpha.read_workflow_result('{contract_address}')")

        return contract_address

    except Exception as e:
        logger.error(f"❌ Workflow deployment failed: {e}")
        logger.warning("   Alpha testnet may be unreachable or feature unavailable.")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_workflow_demo() -> None:
    """Run the complete workflow demo."""
    print("\n" + "=" * 65)
    print("⏰ ML Workflow Demo — Automated On-Chain Inference")
    print("=" * 65)
    print()
    print("⚠️  NOTE: Alpha testnet only — not yet on official testnet")
    print()
    print("Official OG Workflows (pre-deployed):")
    for key, wf in OG_WORKFLOWS.items():
        print(f"  • {key}")
        print(f"    Contract: {wf['contract']}")
        print(f"    Desc    : {wf['description']}")
        print()

    # Part 1: Read from an existing official workflow
    print("=" * 65)
    print("Part 1: Reading from official pre-deployed workflow")
    print("=" * 65)
    read_official_workflow("1hr-volatility-ethusdt")

    # Part 2: Deploy a new custom workflow
    print("\n" + "=" * 65)
    print("Part 2: Deploying a new custom workflow")
    print("=" * 65)
    contract = deploy_custom_workflow()

    if contract:
        # Read result from newly deployed workflow
        print(f"\n📖 Reading result from new workflow...")
        try:
            alpha = _get_alpha()
            result = alpha.read_workflow_result(contract)
            print(f"✅ Inference result: {result}")
        except Exception as e:
            logger.warning(f"Result not yet available: {e}")

    print("\n" + "=" * 65)
    print("💡 When to use workflows vs one-off inference:")
    print("   Workflows    — Continuous predictions, DeFi price feeds,")
    print("                  smart contracts that consume ML outputs")
    print("   One-off      — User-triggered queries, on-demand predictions,")
    print("                  applications that manage their own scheduling")
    print("=" * 65)


if __name__ == "__main__":
    run_workflow_demo()
