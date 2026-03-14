# OpenGradient Developer Cookbook 🍳
> The ultimate collection of boilerplates, snippets, and templates for building
> trustless, verifiable AI applications using the OpenGradient SDK.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Network: Base Sepolia Testnet](https://img.shields.io/badge/Network-Base%20Sepolia-orange)
[![OpenGradient Docs](https://img.shields.io/badge/Docs-docs.opengradient.ai-cyan)](https://docs.opengradient.ai)

---

## 🏗️ Architecture Overview

```
Your App
   │
   ▼
og.LLM (x402 Gateway)
   │  Permit2 $OPG payment on Base Sepolia
   ▼
TEE Node (Intel TDX Confidential Compute)
   │  Hardware-attested code execution
   ▼
OpenAI / Anthropic / Google / xAI API
   │
   ▼
Base Sepolia  ←── $OPG payment + TEE attestation proof
   │
   ▼
OpenGradient Network  ←── Proof settlement (Merkle / Full / Private)
```

Every LLM call through OpenGradient returns a `payment_hash` — a cryptographic
on-chain proof that a specific prompt was processed inside a Trusted Execution
Environment. This makes AI decisions auditable, verifiable, and trustless.

---

## 📚 Table of Contents

### Snippets
| # | File | What it demonstrates |
|---|------|---------------------|
| 01 | [01_llm_completion_basic.py](#01) | Simple verifiable LLM text completion |
| 02 | [02_llm_chat_with_tools.py](#02) | Multi-turn chat with function/tool calling |
| 03 | [03_llm_streaming.py](#03) | Real-time streaming chat output |
| 04 | [04_settlement_modes.py](#04) | PRIVATE / INDIVIDUAL_FULL / BATCH_HASHED modes |
| 05 | [05_model_hub_management.py](#05) | Model Hub: create → version → upload → list |
| 06 | [06_check_opg_balance.py](#06) | Wallet inspector: OPG + ETH balance on Base Sepolia |
| 07 | [07_memsync_personalized_bot.py](#07) | MemSync: store → search → profile → chatbot |
| 08 | [08_ml_inference_alpha.py](#08) | On-chain ML inference (VANILLA / ZKML / TEE) |
| 09 | [09_ml_workflow_deploy.py](#09) | Deploy + read automated ML volatility workflow |
| 10 | [10_permit2_approval.py](#10) | OPG Permit2 token approval flow |
| 11 | [11_langchain_agent.py](#11) | LangChain agent with OG verifiable LLM backend |

### Boilerplates
| Boilerplate | Description |
|-------------|-------------|
| [fastapi-verifiable-backend](./boilerplates/fastapi-verifiable-backend/) | Production FastAPI server with verifiable AI inference endpoints |
| [antigravity-ai-agent](./boilerplates/antigravity-ai-agent/) | Autonomous agent loop with on-chain proof trail |
| [defi-risk-analyzer](./boilerplates/defi-risk-analyzer/) | DeFi smart contract auditor with TEE-verified analysis |
| [memsync-chatbot](./boilerplates/memsync-chatbot/) | Personalized chatbot with persistent MemSync memory |
| [digital-twins-tracker](./boilerplates/digital-twins-tracker/) | Twin.fun share price tracker + AI commentary |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A **testnet-only** Ethereum wallet (never use mainnet funds)
- Test $OPG tokens on Base Sepolia — get them at [faucet.opengradient.ai](https://faucet.opengradient.ai)
- OpenGradient Model Hub account — register at [hub.opengradient.ai](https://hub.opengradient.ai)
- MemSync API key (optional, for snippets 07+) — register at [app.memsync.ai](https://app.memsync.ai)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-org/OpenGradient-Cookbook.git
cd OpenGradient-Cookbook

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your testnet private key and credentials
```

### Environment Setup

```bash
# .env — fill in your values
OG_PRIVATE_KEY=0xYOUR_TESTNET_PRIVATE_KEY
OG_EMAIL=your@email.com
OG_PASSWORD=your_model_hub_password
MEMSYNC_API_KEY=your_memsync_key
```

> ⚠️ **SECURITY**: The private key in `.env` must be a **testnet-only** wallet.
> Never put mainnet funds in a wallet used for development.
> Your `.env` file is in `.gitignore` and will never be committed.

---

## 📝 Snippets

### 01 — LLM Completion Basic {#01}
Simple verifiable text completion. The "Hello World" of OpenGradient.
```bash
python snippets/01_llm_completion_basic.py
```

### 02 — LLM Chat with Tools {#02}
Multi-turn chat with function/tool calling. Build agents that call external APIs.
```bash
python snippets/02_llm_chat_with_tools.py
```

### 03 — LLM Streaming {#03}
Real-time streaming output for terminal apps and web UIs.
```bash
python snippets/03_llm_streaming.py
```

### 04 — Settlement Modes {#04}
Compare PRIVATE / INDIVIDUAL_FULL / BATCH_HASHED — choose the right privacy/cost tradeoff.
```bash
python snippets/04_settlement_modes.py
```

### 05 — Model Hub Management {#05}
Create a model repo, version it, upload an ONNX file, and list files.
```bash
python snippets/05_model_hub_management.py
```

### 06 — Check OPG Balance {#06}
Inspect your wallet's ETH and $OPG balance before running inference.
```bash
python snippets/06_check_opg_balance.py
```

### 07 — MemSync Personalized Bot {#07}
Store conversations → search memories → retrieve user profile using MemSync.
```bash
python snippets/07_memsync_personalized_bot.py
```

### 08 — ML Inference Alpha {#08}
Run on-chain ML model inference in VANILLA, ZKML, and TEE modes (alpha testnet).
```bash
python snippets/08_ml_inference_alpha.py
```

### 09 — ML Workflow Deploy {#09}
Deploy an automated ETH volatility prediction workflow with oracle data feeds.
```bash
python snippets/09_ml_workflow_deploy.py
```

### 10 — Permit2 Approval {#10}
Approve $OPG tokens via Permit2 — required once before any LLM inference.
```bash
python snippets/10_permit2_approval.py
```

### 11 — LangChain Agent {#11}
Use OpenGradient's verifiable LLM as a drop-in LangChain backend.
```bash
python snippets/11_langchain_agent.py
```

---

## 🏗️ Boilerplates

### [FastAPI Verifiable Backend](./boilerplates/fastapi-verifiable-backend/)
A production-ready REST API server with `/infer`, `/chat`, and `/stream` endpoints.
Returns verifiable `payment_hash` with every AI response.

### [Antigravity AI Agent](./boilerplates/antigravity-ai-agent/)
Fully autonomous agent that breaks tasks into steps, executes them with verifiable
LLM inference, and logs a cryptographic proof trail to `agent_log.jsonl`.

### [DeFi Risk Analyzer](./boilerplates/defi-risk-analyzer/)
Analyzes Solidity smart contracts and loan applications using TEE-verified LLM.
Every analysis includes a `payment_hash` for regulatory audit compliance.

### [MemSync Chatbot](./boilerplates/memsync-chatbot/)
A personalized chatbot that remembers users across sessions using MemSync's
semantic memory layer combined with OpenGradient's verifiable LLM.

### [Digital Twins Tracker](./boilerplates/digital-twins-tracker/)
Track Twin.fun share prices, check your holdings, and get AI-generated market
commentary — all with verifiable on-chain proof of the AI analysis.

---

## 🎯 Use Cases

| Domain | Use Case | Key Feature |
|--------|----------|-------------|
| **DeFi** | Smart contract audits, trading agent decisions | `INDIVIDUAL_FULL` settlement — proof of every prompt |
| **Finance** | Loan risk assessment, fraud detection | TEE verification — hardware-attested privacy |
| **Healthcare** | Patient data analysis, clinical decision support | TEE confidential compute — data never exposed |
| **Enterprise AI** | Content moderation, compliance logging | Verifiable audit trails for regulatory requirements |
| **AI Agents** | Autonomous agents with provable actions | `payment_hash` per step — full reasoning transparency |
| **Consumer Apps** | Personalized assistants, tutors, CRM | MemSync — persistent memory across sessions |

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-snippet`
3. Follow the coding standards:
   - Python 3.10+ with full type hints
   - Google-style docstrings on all modules and functions
   - `logging` for operational messages, `print()` for user-facing output
   - All secrets via `os.getenv()` — never hardcoded
4. Test your snippet: `python snippets/your_snippet.py`
5. Open a Pull Request with a clear description

### Adding a New Snippet
- Place it in `snippets/` with the next number prefix (e.g. `12_my_feature.py`)
- Add it to the Table of Contents in this README
- Use `utils/client.py` for SDK initialization

### Adding a New Boilerplate
- Create a new folder in `boilerplates/`
- Include `main.py` (or equivalent), `requirements.txt`, and `README.md`
- The README must include: what it does, how to run, example output

---

## 📖 Resources

- [OpenGradient Docs](https://docs.opengradient.ai)
- [Python SDK Reference](https://docs.opengradient.ai/api_reference/python_sdk/)
- [x402 Gateway Overview](https://docs.opengradient.ai/developers/x402/)
- [MemSync Guide](https://memsync.mintlify.app/)
- [Model Hub](https://hub.opengradient.ai)
- [Block Explorer](https://explorer.opengradient.ai)
- [Testnet Faucet](https://faucet.opengradient.ai)
- [Discord Community](https://discord.gg/SC45QNNMsB)

---

## 📄 License

MIT — see [LICENSE](./LICENSE) for details.
