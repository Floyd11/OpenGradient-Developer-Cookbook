"""
boilerplates/antigravity-ai-agent/agent.py

Fully autonomous AI agent with verifiable on-chain inference and a
cryptographic proof trail. Every reasoning step produces a payment_hash
that can be verified on Base Sepolia.

Architecture:
  ┌─────────────────────────────────────────────┐
  │             VerifiableAgent                  │
  │                                              │
  │  receive_task(task)                          │
  │       ↓                                      │
  │  plan(task) ──── og.LLM (TEE-verified) ──── │
  │       ↓          payment_hash #1             │
  │  for step in plan:                           │
  │    execute_step(step) ── tools (search, ML) ─│
  │       ↓                                      │
  │    verifiable_inference() ─── og.LLM ──────  │
  │       ↓                  payment_hash #N     │
  │    log_result() ──────── agent_log.jsonl ─── │
  │       ↓                                      │
  │  print_proof_trail() ── all payment_hashes ──│
  └─────────────────────────────────────────────┘

Every payment_hash is permanent on-chain proof of:
  - WHAT prompt was used
  - WHICH model processed it
  - WHEN it happened
  - THAT it ran inside a TEE

Run:
    python agent.py
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import opengradient as og
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from tools import analyze_data, format_report, search_web
from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0
LOG_FILE: str = "agent_log.jsonl"

# Use INDIVIDUAL_FULL for max auditability — every prompt is on-chain
AGENT_SETTLEMENT_MODE: og.x402SettlementMode = og.x402SettlementMode.INDIVIDUAL_FULL


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class StepResult:
    """Result from a single agent execution step."""
    step_number: int
    step_name: str
    tool_used: str
    response: str
    payment_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "step": self.step_number,
            "name": self.step_name,
            "tool": self.tool_used,
            "response_summary": self.response[:200] + "..." if len(self.response) > 200 else self.response,
            "payment_hash": self.payment_hash,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# VerifiableAgent
# ---------------------------------------------------------------------------
class VerifiableAgent:
    """
    Autonomous AI agent where every reasoning step is TEE-verified
    and produces a cryptographic on-chain proof.

    Using INDIVIDUAL_FULL settlement mode means every prompt and response
    is stored on-chain — creating a complete, immutable audit trail of
    every decision the agent makes.
    """

    def __init__(self) -> None:
        self._llm: og.LLM = get_llm()
        self._approved: bool = False
        self._step_results: list[StepResult] = []
        self._log_file: str = LOG_FILE

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_approval(self) -> None:
        """Ensure Permit2 OPG allowance (called once)."""
        if not self._approved:
            approval = self._llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
            if approval.tx_hash:
                logger.info(f"💰 Permit2 tx: {BASESCAN_TX_URL}{approval.tx_hash}")
            self._approved = True

    def _log_result(self, result: StepResult) -> None:
        """Append a step result to the JSONL log file."""
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result.to_dict()) + "\n")
        except OSError as e:
            logger.warning(f"Could not write to log file: {e}")

    # ------------------------------------------------------------------
    # Core agent methods
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def verifiable_inference(
        self, prompt: str, step_name: str = "inference"
    ) -> tuple[str, str]:
        """
        Core LLM call — every call is TEE-verified and produces a payment_hash.

        Uses INDIVIDUAL_FULL settlement so the exact prompt and response are
        recorded on-chain for maximum auditability.

        Decorated with @retry for resilience (3 attempts, exponential backoff).

        Args:
            prompt: The prompt to send
            step_name: Human-readable label for logging

        Returns:
            Tuple of (response_text, payment_hash)
        """
        logger.info(f"🤖 verifiable_inference: {step_name}")
        result = await self._llm.completion(
            model=DEFAULT_MODEL,
            prompt=prompt,
            max_tokens=500,
            temperature=0.0,
            x402_settlement_mode=AGENT_SETTLEMENT_MODE,
        )
        return result.completion_output, result.payment_hash

    async def receive_task(self, task: str) -> None:
        """
        Accept a natural language task description.
        Prints the task and resets internal state for a fresh run.
        """
        self._step_results = []
        print(f"\n📥 Task received: {task}")
        logger.info(f"Task: {task}")

    async def plan(self, task: str) -> list[str]:
        """
        Use the verifiable LLM to break a task into executable steps.

        Returns:
            List of step strings (3–5 steps)
        """
        prompt = (
            f"You are an autonomous AI agent. Break this task into 3-4 concrete steps.\n\n"
            f"Task: {task}\n\n"
            f"Format your response as a numbered list only:\n"
            f"1. [step one]\n"
            f"2. [step two]\n"
            f"3. [step three]\n"
            f"(etc.)\n\n"
            f"Be specific and action-oriented."
        )
        response, payment_hash = await self.verifiable_inference(prompt, "planning")

        # Parse numbered list into steps
        steps: list[str] = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and "." in line:
                step = line.split(".", 1)[1].strip()
                if step:
                    steps.append(step)

        if not steps:
            # Fallback if parsing fails
            steps = [line.strip() for line in response.strip().split("\n") if line.strip()][:4]

        # Log the planning step
        result = StepResult(
            step_number=0,
            step_name="Plan",
            tool_used="og.LLM",
            response=response,
            payment_hash=payment_hash,
        )
        self._step_results.append(result)
        self._log_result(result)

        print(f"\n📋 Plan ({len(steps)} steps):")
        for i, step in enumerate(steps, 1):
            print(f"   {i}. {step}")

        return steps

    async def execute_step(self, step: str, step_number: int) -> StepResult:
        """
        Execute a single plan step by routing it to the appropriate tool.

        Routing logic:
          - "search" / "research" / "find" → search_web()
          - "analyze" / "evaluate" / "assess" → analyze_data()
          - "write" / "format" / "summarize" → verifiable_inference() directly
          - default → verifiable_inference() directly

        Args:
            step: Step description
            step_number: Step index (1-based)

        Returns:
            StepResult with response and payment_hash
        """
        step_lower = step.lower()
        payment_hash = ""
        tool_used = "og.LLM"

        print(f"\n▶ Step {step_number}: {step}")

        # Route to appropriate tool
        if any(kw in step_lower for kw in ["search", "research", "find", "look up"]):
            # Extract query from step (simplified)
            search_result = search_web(step)
            tool_used = "search_web"

            # Synthesize the search result with LLM
            synthesis_prompt = (
                f"Step to complete: {step}\n\n"
                f"Search results found:\n{search_result}\n\n"
                f"Extract the key relevant facts from these results."
            )
            response, payment_hash = await self.verifiable_inference(
                synthesis_prompt, f"step_{step_number}_synthesis"
            )

        elif any(kw in step_lower for kw in ["analyze", "analyse", "evaluate", "assess", "examine"]):
            # Use analyze_data tool (async — calls og.LLM internally with TEE verification)
            context = " ".join(
                r.response[:200] for r in self._step_results[-2:]
            )
            response, payment_hash = await analyze_data(context or step, question=step)
            tool_used = "analyze_data"

        else:
            # Default: direct LLM inference
            context = "\n".join(
                f"Step {r.step_number} result: {r.response[:150]}"
                for r in self._step_results[-2:]
            )
            prompt = (
                f"Complete this task step:\n{step}\n\n"
                + (f"Context from previous steps:\n{context}\n\n" if context else "")
                + "Provide a focused, actionable result."
            )
            response, payment_hash = await self.verifiable_inference(
                prompt, f"step_{step_number}"
            )

        result = StepResult(
            step_number=step_number,
            step_name=step[:50],
            tool_used=tool_used,
            response=response,
            payment_hash=payment_hash,
        )
        self._step_results.append(result)
        self._log_result(result)

        print(f"   ✅ {result.response[:120]}...")
        if payment_hash:
            print(f"   🔗 Proof: {BASESCAN_TX_URL}{payment_hash}")

        return result

    def print_proof_trail(self) -> None:
        """Print all payment hashes as a formatted proof trail."""
        print("\n" + "=" * 65)
        print("🔐 AGENT PROOF TRAIL")
        print("=" * 65)
        print("Every reasoning step is TEE-verified on Base Sepolia:\n")

        for r in self._step_results:
            step_label = f"Step {r.step_number}: {r.step_name[:20]:<20}"
            if r.payment_hash:
                print(f"  {step_label} → 🔗 {BASESCAN_TX_URL}{r.payment_hash}")
            else:
                print(f"  {step_label} → (tool-only, no LLM proof)")

        verified = sum(1 for r in self._step_results if r.payment_hash)
        print(f"\n  Total verified steps : {verified}/{len(self._step_results)}")
        print(f"  Log file             : {os.path.abspath(self._log_file)}")
        print(f"\n  ✅ All proofs are permanent on Base Sepolia and cannot be tampered.")
        print("=" * 65)

    async def run(self, task: str) -> str:
        """
        Orchestrate the full agent loop for a given task.

        Flow:
          1. receive_task → reset state
          2. plan → break into steps using verifiable LLM
          3. execute_step → run each step (tools + verifiable LLM)
          4. synthesize → produce final answer
          5. print_proof_trail → display all payment hashes

        Args:
            task: Natural language task description

        Returns:
            Final answer string
        """
        self._ensure_approval()
        await self.receive_task(task)

        # Plan
        steps = await self.plan(task)

        # Execute each step
        for i, step in enumerate(steps, 1):
            try:
                await self.execute_step(step, i)
            except Exception as e:
                logger.error(f"❌ Step {i} failed: {e}")
                print(f"   ❌ Step {i} failed: {e}")

        # Final synthesis
        all_results = "\n".join(
            f"Step {r.step_number} ({r.step_name}): {r.response[:300]}"
            for r in self._step_results[1:]  # skip planning step
        )
        synthesis_prompt = (
            f"Original task: {task}\n\n"
            f"Results from all steps:\n{all_results}\n\n"
            f"Write a clear, concise final answer (3-5 sentences). "
            f"Highlight the key findings."
        )

        print("\n🧠 Synthesizing final answer...")
        final_answer, final_hash = await self.verifiable_inference(
            synthesis_prompt, "final_synthesis"
        )

        # Format and display report
        findings = [r.response[:200] for r in self._step_results[1:]]
        hashes = [r.payment_hash for r in self._step_results]
        report = format_report(findings, title=f"Agent Report: {task[:50]}", payment_hashes=hashes)

        print("\n" + report)
        print(f"\n✅ Final Answer:\n{final_answer}")

        # Proof trail
        self.print_proof_trail()

        return final_answer


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    sample_task = (
        "Research the current state of verifiable AI and write a "
        "3-point summary of why it matters for Web3 applications."
    )
    agent = VerifiableAgent()
    await agent.run(sample_task)


if __name__ == "__main__":
    asyncio.run(main())
