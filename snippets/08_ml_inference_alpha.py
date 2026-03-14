"""
snippets/08_ml_inference_alpha.py — On-Chain ML Inference (Alpha Testnet)

Demonstrates running a traditional ML model (ONNX format) through
OpenGradient's on-chain inference infrastructure in three verification modes:

  VANILLA  — No proof, fastest execution, lowest cost
  ZKML     — Zero-Knowledge proof generated for the inference result
  TEE      — Trusted Execution Environment verification

⚠️  WARNING: This feature is currently ALPHA TESTNET ONLY.
    It is NOT available on the official testnet yet.
    For production LLM inference, use snippets/01_llm_completion_basic.py

The demo model CID used here is a pre-deployed test model on the OpenGradient
Model Hub. In production, you would use your own model's CID from hub.opengradient.ai

Run:
    python snippets/08_ml_inference_alpha.py
"""

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import opengradient as og
from dotenv import load_dotenv

from utils.client import get_client, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Pre-deployed demo model on OpenGradient's alpha testnet Model Hub
DEMO_MODEL_CID: str = "QmbUqS93oc4JTLMHwpVxsE39mhNxy6hpf6Py3r9oANr8aZ"

# Sample multi-type input matching this model's expected schema
DEMO_MODEL_INPUT: dict = {
    "num_input1": [1.0, 2.0, 3.0],   # numeric array
    "num_input2": 10,                  # scalar integer
    "str_input1": ["hello", "ONNX"],  # string array
    "str_input2": " world",            # scalar string
}

OG_EXPLORER_URL: str = "https://explorer.opengradient.ai"


@dataclass
class InferenceResult:
    """Holds the result of a single inference call."""
    mode_name: str
    description: str
    trust_guarantee: str
    model_output: object
    transaction_hash: str | None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_ml_inference_demo() -> None:
    """Run the demo model through all three inference modes."""
    client = get_client()

    print("\n" + "=" * 65)
    print("⚗️  On-Chain ML Inference — Alpha Testnet Demo")
    print("=" * 65)
    print(f"   Model CID : {DEMO_MODEL_CID}")
    print(f"   Input     : {DEMO_MODEL_INPUT}")
    print()
    print("⚠️  NOTE: Alpha testnet only — not yet on official testnet")
    print("=" * 65)

    # Define all three modes to test
    modes: list[tuple[og.InferenceMode, str, str]] = [
        (
            og.InferenceMode.VANILLA,
            "VANILLA",
            "No cryptographic proof — fastest and cheapest.",
        ),
        (
            og.InferenceMode.ZKML,
            "ZKML",
            "Zero-Knowledge proof — proves the model output is correct.",
        ),
        (
            og.InferenceMode.TEE,
            "TEE",
            "Trusted Execution Environment — hardware-level attestation.",
        ),
    ]

    results: list[InferenceResult] = []

    for mode, mode_name, trust_guarantee in modes:
        logger.info(f"🔄 Running inference in {mode_name} mode...")
        try:
            result = client.alpha.infer(
                model_cid=DEMO_MODEL_CID,
                model_input=DEMO_MODEL_INPUT,
                inference_mode=mode,
            )
            tx_hash = getattr(result, "transaction_hash", None)
            results.append(InferenceResult(
                mode_name=mode_name,
                description=trust_guarantee,
                trust_guarantee=trust_guarantee,
                model_output=result.model_output,
                transaction_hash=tx_hash,
            ))
            logger.info(f"✅ {mode_name} complete — tx: {tx_hash or 'N/A'}")

        except Exception as e:
            logger.error(f"❌ {mode_name} inference failed: {e}")
            results.append(InferenceResult(
                mode_name=mode_name,
                description=trust_guarantee,
                trust_guarantee=trust_guarantee,
                model_output=None,
                transaction_hash=None,
            ))

    # Print comparison table
    print(f"\n{'Mode':<10} {'Output':<25} {'Tx Hash':<20}")
    print("-" * 60)
    for r in results:
        output_str = str(r.model_output)[:22] + "..." if r.model_output else "N/A"
        hash_str = (r.transaction_hash[:18] + "...") if r.transaction_hash else "N/A"
        print(f"{r.mode_name:<10} {output_str:<25} {hash_str:<20}")


if __name__ == "__main__":
    run_ml_inference_demo()
