# DeFi Risk Analyzer 🏦

TEE-verified smart contract auditing and financial risk assessment. Every
analysis produces a `payment_hash` — immutable on-chain proof of what
criteria were used, enabling regulatory compliance and audit trails.

## Architecture

```
User / App                    DeFiRiskAnalyzer                   Base Sepolia
     │                                │                                │
     │  1. Contract code / loan data  │                                │
     ├───────────────────────────────►│                                │
     │                                │  2. Format prompt + criteria   │
     │                                │                                │
     │                                │  3. og.LLM.completion()        │
     │                                ├───────────────────────────────►│ TEE Execution
     │                                │                                │ (Intel TDX)
     │                                │  4. completion_output          │
     │                                │     payment_hash (on-chain)    │
     │                                │◄───────────────────────────────┤
     │  5. AnalysisResult             │                                │
     │     .findings (text)           │                                │
     │     .risk_level (enum)         │                                │
     │     .payment_hash (proof) ─────┼────────────────────────────────┘
     │◄───────────────────────────────┤
```

`payment_hash` = permanent on-chain proof that a specific prompt was processed
inside a TEE. Used for regulatory audit trails and dispute resolution.

## Why TEE for DeFi?

In DeFi and finance, you need to **prove** three things about an AI decision:
1. **WHAT prompt** was used (exact analysis criteria)
2. **WHICH model** evaluated the risk
3. **THAT it wasn't tampered** with after the fact

With `INDIVIDUAL_FULL` settlement, all of this is permanently on Base Sepolia.

## Setup

```bash
cd boilerplates/defi-risk-analyzer
pip install -r requirements.txt
cp ../../.env.example .env
```

## Run

```bash
python analyzer.py
```

## Sample Output

```
=====================================================================
📊 Smart Contract Security Audit
=====================================================================
  Input     : // SPDX-License-Identifier: MIT pragma solidity...
  Risk Level: 🔴 CRITICAL

  Findings:
    RISK LEVEL: CRITICAL

    VULNERABILITIES FOUND:
    1. Reentrancy Attack — External call before state update allows
       attacker to recursively drain contract funds.

    RECOMMENDATIONS:
    1. Use Checks-Effects-Interactions pattern: update balances BEFORE
       external calls. Or use OpenZeppelin's ReentrancyGuard.

  💰 Payment Hash : 0xabc123...
  🔗 On-Chain Proof: https://sepolia.basescan.org/tx/0xabc123...
  🤖 Model         : openai/gpt-5
=====================================================================
```

## API Usage

```python
from analyzer import DeFiRiskAnalyzer

analyzer = DeFiRiskAnalyzer()

# Analyze a smart contract
result = await analyzer.analyze_contract(solidity_code)
print(result.risk_level)     # "CRITICAL"
print(result.findings)       # Full analysis text
print(result.payment_hash)   # On-chain proof

# Assess loan risk
result = await analyzer.assess_loan_risk({
    "applicant_income": 75000,
    "credit_score": 720,
    "debt_to_income": 0.35,
    "loan_amount": 250000,
})

# Full 3-phase audit
results = await analyzer.generate_audit_report(contract_code)
# Returns: [security_result, gas_result, logic_result]
```

## Compliance Integration

Store `payment_hash` values in your compliance database alongside decisions:

```python
compliance_record = {
    "decision_id": uuid4(),
    "decision": "DECLINE",
    "applicant_id": "APP-12345",
    "payment_hash": result.payment_hash,
    "basescan_url": result.basescan_url,
    "timestamp": datetime.utcnow().isoformat(),
}
```

This creates an immutable audit trail satisfying requirements for:
- EU AI Act explainability requirements
- Fair lending / ECOA compliance documentation
- DeFi protocol governance audit logs
