"""
utils/client.py — Shared OpenGradient client initialization helpers.

This module provides singleton accessors for the OpenGradient SDK objects:
  - og.LLM     : for verifiable LLM inference via x402 Gateway (needs only private key)
  - og.Alpha   : for on-chain ML inference and workflows (needs only private key)
  - og.ModelHub: for Model Hub operations only (needs email + password)

Note: og.Client was removed from the SDK in version 0.6.0. Use the dedicated
classes above instead — og.LLM, og.Alpha, and og.ModelHub.

All secrets are read from environment variables. A clear ValueError is raised
if required variables are missing, preventing cryptic downstream errors.

Usage:
    from utils.client import get_llm, get_alpha, get_hub, logger
"""

import logging
import os
import sys

import opengradient as og
from dotenv import load_dotenv

# Load .env file if present (no-op in production where env vars are set directly)
load_dotenv()

# ---------------------------------------------------------------------------
_log_level_str: str = os.getenv("LOG_LEVEL", "INFO").upper()
_log_level: int = getattr(logging, _log_level_str, logging.INFO)

logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger: logging.Logger = logging.getLogger("opengradient.cookbook")

# ---------------------------------------------------------------------------
_llm_instance: og.LLM | None = None
_hub_instance: og.ModelHub | None = None


def _require_env(var: str) -> str:
    """Return env var value or raise a descriptive ValueError."""
    value = os.getenv(var)
    if not value:
        raise ValueError(
            f"Missing required environment variable: {var}\n"
            f"Please copy .env.example to .env and fill in your values.\n"
            f"See: https://docs.opengradient.ai/developers/sdk/"
        )
    return value


def get_llm() -> og.LLM:
    """
    Return the singleton og.LLM instance for x402 LLM inference.

    Requires:
        OG_PRIVATE_KEY (env) — testnet wallet private key

    Returns:
        og.LLM: initialized LLM client

    Note:
        Remember to call llm.ensure_opg_approval(opg_amount=5.0) once
        before your first inference call in a session.
    """
    global _llm_instance
    if _llm_instance is None:
        private_key = _require_env("OG_PRIVATE_KEY")
        logger.debug("Initializing og.LLM singleton...")
        _llm_instance = og.LLM(private_key=private_key)
        logger.info("✅ og.LLM initialized (x402 Gateway / Base Sepolia)")
    return _llm_instance


def get_alpha() -> og.Alpha:
    """
    Return a new og.Alpha instance for on-chain ML inference and workflows.

    Per official docs (docs.opengradient.ai/developers/sdk/ml_inference.html):
    ML inference and Workflows use the STANDALONE og.Alpha class.

    Usage:
        alpha = get_alpha()
        result = alpha.infer(model_cid=..., model_input=..., inference_mode=...)
        contract = alpha.new_workflow(...)
        alpha.run_workflow(contract_address)
        result = alpha.read_workflow_result(contract_address)

    ⚠️  Alpha testnet only — not yet on official testnet.

    Requires:
        OG_PRIVATE_KEY (env) — testnet wallet private key

    Returns:
        og.Alpha: initialized alpha inference client
    """
    private_key = _require_env("OG_PRIVATE_KEY")
    logger.debug("Initializing og.Alpha instance...")
    return og.Alpha(private_key=private_key)


def get_hub() -> og.ModelHub:
    """
    Return the singleton og.ModelHub instance for model management only.

    Requires:
        OG_EMAIL    (env) — Model Hub account email
        OG_PASSWORD (env) — Model Hub account password

    Returns:
        og.ModelHub: initialized hub client
    """
    global _hub_instance
    if _hub_instance is None:
        email = _require_env("OG_EMAIL")
        password = _require_env("OG_PASSWORD")
        logger.debug("Initializing og.ModelHub singleton...")
        _hub_instance = og.ModelHub(email=email, password=password)
        logger.info("✅ og.ModelHub initialized")
    return _hub_instance
