# FastAPI Verifiable Backend 🔐

A production-ready REST API that exposes OpenGradient's verifiable LLM inference
as HTTP endpoints. Every AI response comes with a `payment_hash` — cryptographic
proof the inference ran inside a TEE (Trusted Execution Environment).

---

## Architecture

```
Client (curl / frontend)
        │
        ▼
FastAPI Server (this boilerplate)
        │  POST /infer | POST /chat | POST /stream
        ▼
og.LLM — x402 Gateway
        │  Permit2 $OPG payment
        ▼
TEE Node (Intel TDX)
        │
        ▼
OpenAI / Anthropic / Google API
        │
        ▼
Base Sepolia ← payment_hash proof on-chain
```

---

## Setup

```bash
cd boilerplates/fastapi-verifiable-backend
pip install -r requirements.txt
cp ../../.env.example .env
# Edit .env with your OG_PRIVATE_KEY
```

## Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open: **http://localhost:8000/docs** — interactive Swagger UI

---

## Endpoints

### `GET /health`
```bash
curl http://localhost:8000/health
```
```json
{
  "status": "ok",
  "network": "base-sepolia",
  "permit2_approved": true,
  "og_explorer": "https://explorer.opengradient.ai"
}
```

### `POST /infer` — Text Completion
```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain verifiable AI in one sentence.",
    "model": "gpt-5",
    "max_tokens": 100,
    "settlement_mode": "batch_hashed"
  }'
```
```json
{
  "response": "Verifiable AI uses cryptographic proofs to guarantee that AI inference...",
  "payment_hash": "0xabc123...",
  "basescan_url": "https://sepolia.basescan.org/tx/0xabc123...",
  "model_used": "gpt-5",
  "settlement_mode": "batch_hashed",
  "tool_calls": null
}
```

### `POST /chat` — Multi-Turn Chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is OpenGradient?"}
    ],
    "model": "claude-sonnet-4-6",
    "settlement_mode": "individual_full"
  }'
```

### `POST /stream` — Server-Sent Events
```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Tell me about TEE security"}], "model": "gpt-5"}'
```

**Frontend (JavaScript):**
```javascript
const response = await fetch('/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages: [...], model: 'gpt-5' })
});
const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = new TextDecoder().decode(value);
  console.log(text); // "data: token\n\n"
}
```

---

## Available Models

| model string | Provider | Notes |
|---|---|---|
| `gpt-5` | OpenAI | Latest GPT-5 |
| `gpt-5-mini` | OpenAI | Smaller/faster |
| `gpt-4.1` | OpenAI | GPT-4.1 (2025-04-14) |
| `claude-sonnet-4-6` | Anthropic | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Anthropic | Claude Opus 4.6 |
| `gemini-2.5-flash` | Google | Fast Gemini |
| `grok-4-fast` | xAI | Fast Grok-4 |

## Settlement Modes

| mode | Privacy | Cost | On-Chain Data |
|---|---|---|---|
| `private` | MAX | LOW | None |
| `individual_full` | MIN | HIGH | Full prompt+response |
| `batch_hashed` | MED | MED | Merkle hashes (default) |

---

## Production Deployment

```bash
# With Gunicorn for multi-worker production
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Restrict CORS in `main.py` before deploying:
```python
allow_origins=["https://your-frontend-domain.com"]
```
