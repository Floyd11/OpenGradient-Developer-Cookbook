"""
snippets/09_ml_workflow_deploy.py — ML Workflow Deployment & Reading

Demonstrates deploying and consuming automated ML workflows on OpenGradient.
Workflows automatically:
  - Collect live price data from on-chain oracles (e.g., ETH/USD OHLC candles)
  - Execute ML model inference on a schedule
  - Store results on-chain for applications to consume

⚠️  WARNING: Alpha testnet only — not yet on official testnet.

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

from utils.client import get_client, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Official OpenGradient ML Workflow Contracts
# ---------------------------------------------------------------------------
OG_WORKFLOWS: dict[str, dict] = {
    "1hr-volatility-ethusdt": {
        "contract": "0xD5629A5b95dde11e4B5772B5Ad8a13B933e33845",
        "model_cid": "QmRhcpDXfYCKsimTmJYrAVM4Bbvck59Zb2onj3MHv9Kw5N",
        "description": "1-hour ETH/USD volatility prediction",
    },
}

OG_EXPLORER_URL: str = "https://explorer.opengradient.ai"


def read_official_workflow(workflow_key: str = "1hr-volatility-ethusdt") -> None:
    """Read the latest result from an official pre-deployed OG workflow."""
    client = get_client()
    workflow = OG_WORKFLOWS[workflow_key]
    contract_address: str = workflow["contract"]

    print(f"\n📡 Reading from official OG workflow: {workflow_key}")
    try:
        # Manually trigger a fresh inference
        client.alpha.run_workflow(contract_address)
        # Read the latest result
        result = client.alpha.read_workflow_result(contract_address)
        print(f"\n✅ Latest workflow result: {result}")
    except Exception as e:
        logger.error(f"❌ Failed to read workflow: {e}")


def deploy_custom_workflow() -> str | None:
    """Deploy a new ML workflow."""
    client = get_client()

    # Define the data input query
    input_query = HistoricalInputQuery(
        base="ETH",
        quote="USD",
        total_candles=10,
        candle_duration_in_mins=30,
        order=CandleOrder.ASCENDING,
        candle_types=[CandleType.OPEN, CandleType.HIGH, CandleType.LOW, CandleType.CLOSE],
    )

    # Define the execution schedule
    scheduler_params = SchedulerParams(
        frequency=3600,
        duration_hours=720,
    )

    model_cid = OG_WORKFLOWS["1hr-volatility-ethusdt"]["model_cid"]

    try:
        contract_address = client.alpha.new_workflow(
            model_cid=model_cid,
            input_query=input_query,
            input_tensor_name="open_high_low_close",
            scheduler_params=scheduler_params,
        )
        print(f"\n✅ Workflow deployed successfully: {contract_address}")
        return contract_address
    except Exception as e:
        logger.error(f"❌ Workflow deployment failed: {e}")
        return None


if __name__ == "__main__":
    read_official_workflow()
