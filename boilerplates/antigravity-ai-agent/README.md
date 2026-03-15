# Antigravity AI Agent 🤖

An autonomous AI agent where every reasoning step is TEE-verified and produces
a cryptographic on-chain proof trail. Based on the architecture from
[og-agent-starter](https://github.com/OpenGradient/og-agent-starter).

---

## Architecture

```
Task Input
    │
    ▼
plan() ──────────── og.LLM (TEE) ──── payment_hash #1
    │
    ▼
execute_step() ─────────────────────────────────────────
  ├─ search_web()    → stub (replace with Tavily/SerpAPI)
  ├─ analyze_data()  → og.LLM (TEE) ──── payment_hash #N
  └─ direct LLM      → og.LLM (TEE) ──── payment_hash #N
    │
    ▼
final_synthesis() ─── og.LLM (TEE) ──── payment_hash #last
    │
    ▼
PROOF TRAIL ─── all hashes logged to agent_log.jsonl
```

**Settlement Mode**: `INDIVIDUAL_FULL` — every prompt and response stored on-chain.

---

## Setup

```bash
cd boilerplates/antigravity-ai-agent
pip install -r requirements.txt
cp ../../.env.example .env
# Edit .env with OG_PRIVATE_KEY, OG_EMAIL, OG_PASSWORD
```

## Run

```bash
python agent.py
```

## Sample Output

```
📥 Task received: Research the current state of verifiable AI...

📋 Plan (3 steps):
   1. Search for recent developments in verifiable AI
   2. Analyze the key use cases for Web3 applications
   3. Synthesize findings into a 3-point summary

▶ Step 1: Search for recent developments...
   ✅ OpenGradient uses TEE for hardware-attested LLM inference...
   🔗 Proof: https://sepolia.basescan.org/tx/0xabc123...

▶ Step 2: Analyze key use cases...
   ✅ DeFi protocols, healthcare, and compliance systems benefit most...
   🔗 Proof: https://sepolia.basescan.org/tx/0xdef456...

▶ Step 3: Synthesize findings...
   ✅ Verifiable AI creates trustless AI interactions on-chain...
   🔗 Proof: https://sepolia.basescan.org/tx/0x789abc...

✅ Final Answer:
Verifiable AI represents a paradigm shift where every AI decision...

==================================================================
🔐 AGENT PROOF TRAIL
==================================================================
  Step 0: Plan                 → 🔗 https://sepolia.basescan.org/tx/0x...
  Step 1: Search for recent    → 🔗 https://sepolia.basescan.org/tx/0x...
  Step 2: Analyze key use      → 🔗 https://sepolia.basescan.org/tx/0x...
  Step 3: Synthesize findings  → 🔗 https://sepolia.basescan.org/tx/0x...

  Total verified steps : 4/4
  ✅ All proofs permanent on Base Sepolia — cannot be tampered.
```

---

## Customizing

**Add real web search** (replace stub in `tools.py`):
```python
# Option A: Tavily (recommended for agents)
pip install tavily-python
from tavily import TavilyClient
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
return client.search(query)["results"][0]["content"]
```

**Add on-chain transactions** (Coinbase AgentKit):
```python
pip install cdp-sdk cdp-agentkit-core
# See: https://github.com/coinbase/cdp-agentkit
```

**Change the task**:
```python
agent = VerifiableAgent()
await agent.run("Analyze ETH/USD volatility patterns from the past week")
```

---

## Log File

Every inference is logged to `agent_log.jsonl`:
```json
{"step": 1, "name": "Search for recent", "tool": "search_web", "response_summary": "...", "payment_hash": "0x...", "timestamp": "2026-03-14T10:00:00Z"}
```
