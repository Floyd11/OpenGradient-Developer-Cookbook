"""
boilerplates/defi-risk-analyzer/analyzer.py

DeFi smart contract risk analyzer using OpenGradient's TEE-verified LLM.
Every analysis includes a payment_hash — cryptographic proof that the
analysis criteria and prompts are on-chain for regulatory compliance.

Use Cases:
  - Smart contract security audits with verifiable analysis criteria
  - Loan risk assessments with auditable prompt trail
  - DeFi protocol parameter analysis
  - Regulatory compliance documentation for AI-assisted decisions

Why TEE matters here:
  In DeFi and financial services, you often need to prove:
    1. WHAT analysis criteria were used (the exact prompt)
    2. WHICH model evaluated the risk
    3. THAT the analysis wasn't tampered with after the fact

  With INDIVIDUAL_FULL settlement, all of this is on-chain and immutable.

Run:
    python analyzer.py
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import opengradient as og
from dotenv import load_dotenv

from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Use INDIVIDUAL_FULL for financial compliance — full prompt on-chain
SETTLEMENT_MODE: og.x402SettlementMode = og.x402SettlementMode.INDIVIDUAL_FULL
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AnalysisResult:
    """Result of a smart contract or risk analysis."""
    analysis_type: str
    input_summary: str
    findings: str
    risk_level: RiskLevel
    payment_hash: str
    basescan_url: str
    model_used: str

    def print(self) -> None:
        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
        print(f"\n{'=' * 65}")
        print(f"📊 {self.analysis_type}")
        print(f"{'=' * 65}")
        print(f"  Input     : {self.input_summary[:80]}...")
        print(f"  Risk Level: {risk_emoji.get(self.risk_level, '⚪')} {self.risk_level}")
        print(f"\n  Findings:\n{self._indent(self.findings)}")
        print(f"\n  💰 Payment Hash : {self.payment_hash}")
        print(f"  🔗 On-Chain Proof: {self.basescan_url}")
        print(f"  🤖 Model         : {self.model_used}")
        print(f"{'=' * 65}")

    @staticmethod
    def _indent(text: str, spaces: int = 4) -> str:
        return "\n".join(" " * spaces + line for line in text.split("\n"))


# ---------------------------------------------------------------------------
# DeFiRiskAnalyzer
# ---------------------------------------------------------------------------
class DeFiRiskAnalyzer:
    """
    Verifiable DeFi risk analysis using OpenGradient's TEE-backed LLM.

    All analysis calls use INDIVIDUAL_FULL settlement — the exact prompt
    and response are stored on Base Sepolia for compliance documentation.
    """

    def __init__(self) -> None:
        self._llm = get_llm()
        self._approved = False

    def _ensure_approval(self) -> None:
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

    def _parse_risk_level(self, text: str) -> RiskLevel:
        """Extract risk level from analysis text."""
        text_upper = text.upper()
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if level in text_upper:
                return RiskLevel(level)
        return RiskLevel.MEDIUM

    async def _analyze(self, prompt: str, analysis_type: str, input_summary: str) -> AnalysisResult:
        """Internal helper: run a verifiable analysis and return structured result."""
        self._ensure_approval()
        logger.info(f"🔍 Running {analysis_type}...")
        try:
            result = await self._llm.completion(
                model=DEFAULT_MODEL,
                prompt=prompt,
                max_tokens=600,
                temperature=0.0,
                x402_settlement_mode=SETTLEMENT_MODE,
            )
            risk_level = self._parse_risk_level(result.completion_output)
            return AnalysisResult(
                analysis_type=analysis_type,
                input_summary=input_summary,
                findings=result.completion_output,
                risk_level=risk_level,
                payment_hash=result.payment_hash,
                basescan_url=f"{BASESCAN_TX_URL}{result.payment_hash}",
                model_used=DEFAULT_MODEL.value,
            )
        except Exception as e:
            logger.error(f"❌ {analysis_type} failed: {e}")
            raise

    async def analyze_contract(self, contract_code: str) -> AnalysisResult:
        """
        Analyze a Solidity smart contract for security vulnerabilities.

        Checks for:
          - Reentrancy attacks
          - Integer overflow/underflow
          - Access control issues
          - Flash loan vulnerabilities
          - Oracle manipulation risks

        Args:
            contract_code: Solidity source code

        Returns:
            AnalysisResult with findings and on-chain proof
        """
        prompt = (
            "You are an expert smart contract security auditor.\n\n"
            "Analyze this Solidity code for security vulnerabilities:\n\n"
            f"```solidity\n{contract_code}\n```\n\n"
            "Structure your response as:\n"
            "RISK LEVEL: [CRITICAL/HIGH/MEDIUM/LOW]\n\n"
            "VULNERABILITIES FOUND:\n"
            "1. [vulnerability name] — [description and impact]\n"
            "(list all found, or 'None' if clean)\n\n"
            "RECOMMENDATIONS:\n"
            "1. [specific fix]\n\n"
            "SUMMARY: [1-2 sentence overall assessment]"
        )
        return await self._analyze(
            prompt=prompt,
            analysis_type="Smart Contract Security Audit",
            input_summary=contract_code[:80],
        )

    async def assess_loan_risk(self, loan_data: dict) -> AnalysisResult:
        """
        Assess loan application risk using verifiable AI analysis.

        The payment_hash provides an auditable record of what criteria
        were used to make the risk assessment — critical for fair lending
        compliance and regulatory review.

        Args:
            loan_data: Dict with applicant_income, credit_score,
                       debt_to_income, loan_amount

        Returns:
            AnalysisResult with risk assessment and on-chain proof
        """
        prompt = (
            "You are a financial risk assessment AI.\n\n"
            "Assess this loan application:\n\n"
            f"  Applicant Annual Income : ${loan_data.get('applicant_income', 0):,}\n"
            f"  Credit Score           : {loan_data.get('credit_score', 0)}\n"
            f"  Debt-to-Income Ratio   : {loan_data.get('debt_to_income', 0):.0%}\n"
            f"  Requested Loan Amount  : ${loan_data.get('loan_amount', 0):,}\n\n"
            "Provide:\n"
            "RISK LEVEL: [CRITICAL/HIGH/MEDIUM/LOW]\n\n"
            "RISK FACTORS:\n"
            "- [List key risk factors]\n\n"
            "POSITIVE FACTORS:\n"
            "- [List mitigating factors]\n\n"
            "RECOMMENDATION: [APPROVE / APPROVE_WITH_CONDITIONS / DECLINE]\n\n"
            "RATIONALE: [2-3 sentence explanation]"
        )
        input_summary = (
            f"Income: ${loan_data.get('applicant_income', 0):,}, "
            f"Score: {loan_data.get('credit_score', 0)}, "
            f"DTI: {loan_data.get('debt_to_income', 0):.0%}, "
            f"Loan: ${loan_data.get('loan_amount', 0):,}"
        )
        return await self._analyze(
            prompt=prompt,
            analysis_type="Loan Risk Assessment",
            input_summary=input_summary,
        )

    async def generate_audit_report(self, contract_code: str) -> list[AnalysisResult]:
        """
        Generate a comprehensive multi-step audit report for a contract.

        Runs three sequential analyses:
          1. Security vulnerability scan
          2. Gas optimization check
          3. Business logic review

        Each step produces a separate payment_hash — a verifiable chain
        of evidence for the complete audit.

        Args:
            contract_code: Solidity source code

        Returns:
            List of AnalysisResult (one per audit phase)
        """
        results = []

        # Phase 1: Security
        logger.info("🔒 Phase 1: Security analysis...")
        security = await self.analyze_contract(contract_code)
        results.append(security)

        # Phase 2: Gas optimization
        gas_prompt = (
            "You are a Solidity gas optimization expert.\n\n"
            f"Analyze this contract for gas inefficiencies:\n\n```solidity\n{contract_code}\n```\n\n"
            "RISK LEVEL: [HIGH = very expensive / MEDIUM = some waste / LOW = well-optimized]\n\n"
            "GAS ISSUES:\n"
            "1. [issue] — [estimated extra gas cost]\n\n"
            "OPTIMIZATIONS:\n"
            "1. [specific optimization]\n\n"
            "ESTIMATED SAVINGS: [X% gas reduction if optimizations applied]"
        )
        gas_result = await self._analyze(
            prompt=gas_prompt,
            analysis_type="Gas Optimization Analysis",
            input_summary=contract_code[:80],
        )
        results.append(gas_result)

        # Phase 3: Business logic
        logic_prompt = (
            "You are a smart contract business logic auditor.\n\n"
            f"Review this contract's business logic:\n\n```solidity\n{contract_code}\n```\n\n"
            "RISK LEVEL: [CRITICAL/HIGH/MEDIUM/LOW]\n\n"
            "LOGIC ISSUES:\n"
            "- [Any business logic vulnerabilities or edge cases]\n\n"
            "ACCESS CONTROL:\n"
            "- [Analysis of who can do what]\n\n"
            "OVERALL ASSESSMENT: [1-2 sentences]"
        )
        logic_result = await self._analyze(
            prompt=logic_prompt,
            analysis_type="Business Logic Review",
            input_summary=contract_code[:80],
        )
        results.append(logic_result)

        return results


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
async def run_demo() -> None:
    """Run the DeFi risk analyzer with sample inputs."""
    analyzer = DeFiRiskAnalyzer()

    print("\n" + "=" * 65)
    print("🏦 DeFi Risk Analyzer — Powered by OpenGradient TEE")
    print("=" * 65)
    print(
        "\nℹ️  All analysis uses INDIVIDUAL_FULL settlement —\n"
        "   full prompts and responses are stored on Base Sepolia\n"
        "   for regulatory audit compliance."
    )

    # ---------------------------------------------------------------
    # Demo 1: Vulnerable smart contract
    # ---------------------------------------------------------------
    print("\n" + "─" * 65)
    print("Demo 1: Smart Contract with Reentrancy Vulnerability")
    print("─" * 65)

    vulnerable_contract = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableBank {
    mapping(address => uint256) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // ⚠️ VULNERABLE: reentrancy attack possible
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // External call BEFORE state update — classic reentrancy
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;  // State updated AFTER external call
    }
}
"""
    try:
        result = await analyzer.analyze_contract(vulnerable_contract)
        result.print()
    except Exception as e:
        print(f"❌ Contract analysis failed: {e}")

    # ---------------------------------------------------------------
    # Demo 2: Loan risk assessment
    # ---------------------------------------------------------------
    print("\n" + "─" * 65)
    print("Demo 2: Loan Application Risk Assessment")
    print("─" * 65)

    loan_applications = [
        {
            "applicant_income": 75000,
            "credit_score": 720,
            "debt_to_income": 0.35,
            "loan_amount": 250000,
        },
        {
            "applicant_income": 35000,
            "credit_score": 580,
            "debt_to_income": 0.62,
            "loan_amount": 200000,
        },
    ]

    for i, loan in enumerate(loan_applications, 1):
        print(f"\nApplication #{i}:")
        try:
            result = await analyzer.assess_loan_risk(loan)
            result.print()
        except Exception as e:
            print(f"❌ Loan assessment failed: {e}")

    print("\n" + "=" * 65)
    print("✅ DeFi Risk Analyzer demo complete!")
    print("=" * 65)
    print(
        "\n💡 Each payment_hash above proves:\n"
        "   • What criteria were used for the analysis\n"
        "   • Which model evaluated the risk\n"
        "   • That the analysis cannot be backdated or altered\n"
        "   → Use for regulatory audits, compliance documentation, dispute resolution"
    )


if __name__ == "__main__":
    asyncio.run(run_demo())
