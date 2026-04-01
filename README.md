# OpenGradient Developer Cookbook

[![OpenGradient SDK](https://img.shields.io/badge/OpenGradient_SDK-0.9.x-blueviolet?logo=python)](https://pypi.org/project/opengradient/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![Base Sepolia](https://img.shields.io/badge/Network-Base_Sepolia_Testnet-orange?logo=ethereum)](https://docs.base.org/chain/network-information/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A curated collection of production-ready code snippets, boilerplates, and
patterns for building applications on the [OpenGradient](https://opengradient.ai)
platform — the verifiable AI inference network.

> **This cookbook is the foundation for the [OG Helper Telegram Bot](https://t.me/OGHelperBot)
> which serves these examples to developers on demand.**

---

## What is OpenGradient?

OpenGradient provides **verifiable AI inference** — every LLM call runs inside a
Trusted Execution Environment (TEE) and settles payment on Base Sepolia via the
x402 protocol. Each inference returns a `transaction_hash` proving:

- Which exact model was used
- What the exact input and output were
- That the computation happened in an isolated secure enclave

---

## Repository Structure

```
OpenGradient-Developer-Cookbook/
├── snippets/                    # Standalone runnable examples
│   ├── 01_llm_completion_basic.py   # Single completion + proof
│   ├── 02_llm_chat_with_tools.py    # Tool calling / function calling
│   ├── 03_llm_streaming.py          # Streaming completions
│   ├── 04_settlement_modes.py       # PRIVATE / INDIVIDUAL / BATCH settlement
│   ├── 05_model_hub_upload.py       # Upload ONNX model to Model Hub
│   ├── 06_check_opg_balance.py      # Wallet inspector (ETH + OPG + Permit2)
│   ├── 07_memsync_persistent.py     # Persistent AI memory via MemSync
│   ├── 08_ml_inference_alpha.py     # On-chain ONNX inference (alpha testnet)
│   ├── 09_workflow_alpha.py         # On-chain ML workflow (alpha testnet)
│   ├── 10_permit2_approval.py       # Manual Permit2 OPG allowance approval
│   └── 11_langchain_agent.py        # LangGraph ReAct agent (og.agents adapter)
├── utils/
│   └── client.py                    # Singleton accessors: get_llm, get_alpha, get_hub
├── .env.example                     # Environment variable template
├── requirements.txt                 # Python dependencies
└── README.md
```

---

## Quick Start

### Prerequisites

- Python **3.11+** (required by `opengradient >= 0.6.0`)
- A testnet wallet with `OG_PRIVATE_KEY` (Base Sepolia)
- $OPG test tokens from the [faucet](https://faucet.opengradient.ai)
- ETH for gas from [Base Sepolia faucet](https://docs.base.org/tools/network-faucets)

### Installation

```bash
git clone https://github.com/Floyd11/OpenGradient-Developer-Cookbook.git
cd OpenGradient-Developer-Cookbook

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env — set OG_PRIVATE_KEY (testnet wallet only, never mainnet!)
```

### Verify your wallet

```bash
# Check ETH balance, $OPG balance, and Permit2 allowance
python snippets/06_check_opg_balance.py
```

### Run your first inference

```bash
python snippets/01_llm_completion_basic.py
```

---

## Snippets Overview

| # | Snippet | What it demonstrates |
|---|---------|----------------------|
| 01 | `01_llm_completion_basic.py` | Single verifiable completion + `transaction_hash` proof |
| 02 | `02_llm_chat_with_tools.py` | Tool calling / function calling with TEE-verified LLM |
| 03 | `03_llm_streaming.py` | Real-time streaming completions |
| 04 | `04_settlement_modes.py` | `PRIVATE`, `INDIVIDUAL_FULL`, `BATCH_HASHED` settlement |
| 05 | `05_model_hub_upload.py` | Upload + manage ONNX models on Model Hub |
| 06 | `06_check_opg_balance.py` | Inspect ETH / $OPG / Permit2 allowance |
| 07 | `07_memsync_persistent.py` | Persistent AI memory via MemSync API |
| 08 | `08_ml_inference_alpha.py` | VANILLA / ZKML / TEE on-chain ONNX inference ⚠️ alpha |
| 09 | `09_workflow_alpha.py` | Deploy + run on-chain ML workflow ⚠️ alpha |
| 10 | `10_permit2_approval.py` | Manual Permit2 $OPG allowance management |
| 11 | `11_langchain_agent.py` | LangGraph ReAct agent via `og.agents.langchain_adapter()` |

---

## Supported Models (SDK 0.9.3+)

| Provider | Model enum | Notes |
|----------|-----------|-------|
| OpenAI | `og.TEE_LLM.GPT_5` | Default recommended |
| OpenAI | `og.TEE_LLM.GPT_5_MINI` | Faster / cheaper |
| OpenAI | `og.TEE_LLM.GPT_5_2` | Latest GPT-5 variant |
| OpenAI | `og.TEE_LLM.GPT_4_1_2025_04_14` | GPT-4.1 |
| OpenAI | `og.TEE_LLM.O4_MINI` | Reasoning model |
| Anthropic | `og.TEE_LLM.CLAUDE_SONNET_4_6` | Recommended Claude |
| Anthropic | `og.TEE_LLM.CLAUDE_SONNET_4_5` | Claude Sonnet 4.5 |
| Anthropic | `og.TEE_LLM.CLAUDE_OPUS_4_6` | Most capable Claude |
| Anthropic | `og.TEE_LLM.CLAUDE_OPUS_4_5` | Claude Opus 4.5 |
| Anthropic | `og.TEE_LLM.CLAUDE_HAIKU_4_5` | Fast / lightweight |
| Google | `og.TEE_LLM.GEMINI_3_PRO` | Latest Gemini |
| Google | `og.TEE_LLM.GEMINI_3_FLASH` | Fast Gemini 3 |
| Google | `og.TEE_LLM.GEMINI_2_5_PRO` | Gemini 2.5 Pro |
| Google | `og.TEE_LLM.GEMINI_2_5_FLASH` | Gemini 2.5 Flash |
| Google | `og.TEE_LLM.GEMINI_2_5_FLASH_LITE` | Lightweight Flash |
| xAI | `og.TEE_LLM.GROK_4` | Grok 4 |
| xAI | `og.TEE_LLM.GROK_4_FAST` | Grok 4 Fast |
| xAI | `og.TEE_LLM.GROK_4_1_FAST` | Grok 4.1 Fast |
| xAI | `og.TEE_LLM.GROK_4_1_FAST_NON_REASONING` | Grok 4.1 non-reasoning |

---

## Architecture: `utils/client.py`

All snippets share a single `utils/client.py` that provides lazy-initialized
singleton accessors:

```python
from utils.client import get_llm, get_alpha, get_hub

# LLM inference (verifiable via x402 Gateway) — needs OG_PRIVATE_KEY
llm = get_llm()

# On-chain ML inference / workflows (alpha testnet) — needs OG_PRIVATE_KEY
alpha = get_alpha()

# Model Hub management — needs OG_EMAIL + OG_PASSWORD
hub = get_hub()
```

> **Note:** `og.Client` was removed from the SDK in version 0.6.0.
> Use the dedicated classes above (`og.LLM`, `og.Alpha`, `og.ModelHub`) instead.

---

## Environment Variables

See [`.env.example`](.env.example) for the full template.

| Variable | Required | Description |
|----------|----------|-------------|
| `OG_PRIVATE_KEY` | ✅ Always | Testnet wallet private key (Base Sepolia — **never use mainnet!**) |
| `OG_EMAIL` | Model Hub only | OpenGradient Model Hub account email |
| `OG_PASSWORD` | Model Hub only | OpenGradient Model Hub account password |
| `RPC_URL` | Optional | Base Sepolia RPC (default: `https://sepolia.base.org`) |
| `CHAIN_ID` | Optional | Chain ID (default: `84532`) |
| `OPG_TOKEN_CONTRACT` | Optional | OPG ERC-20 address (default: `0x240b09731D96979f50B2C649C9CE10FcF9C7987F`) |
| `LOG_LEVEL` | Optional | Logging verbosity: `DEBUG`, `INFO`, `WARNING` (default: `INFO`) |

---

## Security Notes

- 🔐 **Testnet only**: `OG_PRIVATE_KEY` must be a dedicated testnet wallet. Never use a mainnet private key.
- 🚫 **Never commit `.env`**: it is in `.gitignore` by default.
- ✅ **Permit2 pattern**: the x402 Gateway uses [Permit2](https://github.com/Uniswap/permit2) for gasless $OPG spending approval — no raw `approve()` calls needed.

---

## Resources

- 📖 [OpenGradient Docs](https://docs.opengradient.ai)
- 🐍 [OpenGradient Python SDK on PyPI](https://pypi.org/project/opengradient/)
- 🤖 [OG Agent Starter](https://github.com/OpenGradient/og-agent-starter)
- 💬 [Discord Community](https://discord.gg/axammqTRDz)
- 🚧 [OG Explorer (testnet)](https://explorer.opengradient.ai)
- 🚰 [OPG Faucet](https://faucet.opengradient.ai)
