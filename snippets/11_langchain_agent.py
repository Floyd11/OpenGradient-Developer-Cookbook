"""
snippets/11_langchain_agent.py — LangChain Agent with OpenGradient Verifiable LLM

Demonstrates using OpenGradient's TEE-verified LLM as the reasoning backbone
of a LangChain agent.
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
# OpenGradient LangChain LLM Wrapper
# ---------------------------------------------------------------------------
class OGVerifiableLLM:
    """
    Wraps og.LLM as a synchronous callable compatible with LangChain.
    """

    def __init__(self, model: og.TEE_LLM = og.TEE_LLM.GPT_5, max_tokens: int = 1000) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._llm = get_llm()
        self.payment_hashes: list[str] = []

    def __call__(self, prompt: str) -> str:
        try:
            result = asyncio.run(
                self._llm.completion(
                    model=self.model,
                    prompt=prompt,
                    max_tokens=self.max_tokens,
                    temperature=0.0,
                )
            )
            self.payment_hashes.append(result.payment_hash)
            return result.completion_output
        except Exception as e:
            logger.error(f"❌ OG LLM inference failed: {e}")
            raise


if __name__ == "__main__":
    print("🤖 LangChain Agent Wrapper Demo")
    llm = OGVerifiableLLM()
    resp = llm("Explain why verifiable AI matters.")
    print(f"Response: {resp}")
    print(f"Proof: {llm.payment_hashes[-1]}")
