# MemSync Chatbot 🧠

A personalized AI chatbot that remembers users across sessions using
MemSync's semantic memory layer and OpenGradient's verifiable LLM.

---

## Architecture

```
User message
     │
     ▼
MemSync search ──── POST /memories/search
     │  (relevant memories + user_bio)
     ▼
OpenGradient LLM ─── TEE-verified inference
     │  (enriched system prompt + memory context)
     ▼
Response + payment_hash
     │
     ▼
MemSync store ──── POST /memories
     │  (auto-extracts new facts from conversation)
     ▼
Persistent memory for next session
```

---

## Setup

```bash
cd boilerplates/memsync-chatbot
pip install -r requirements.txt
cp ../../.env.example .env
```

Edit `.env`:
```
OG_PRIVATE_KEY=0xYOUR_TESTNET_KEY
MEMSYNC_API_KEY=your_memsync_key  # from app.memsync.ai/dashboard/api-keys
```

## Run

```bash
python chatbot.py
```

---

## Example Conversation

**Session 1:**
```
You: Hi! I'm a Python developer working on a DeFi protocol.
Bot: Great to meet you! What kind of DeFi protocol are you building?

You: An automated market maker with AI-driven fee adjustment.
Bot: That's a fascinating use case — AI-driven AMM fees could significantly
     optimize capital efficiency...
```

**Session 2 (next day):**
```
You: I'm having trouble with the fee calculation logic.
Bot: Happy to help! Given your work on the AI-driven AMM fee adjustment
     system, are you running into issues with the fee curve parameters
     or the ML model integration?
     # ^ Bot remembers from Session 1!
```

---

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `semantic` | Lasting facts about the user | "User is a Python developer" |
| `episodic` | Time-bound events | "User mentioned fee calculation issue on March 14" |

---

## Commands (Interactive REPL)

| Command | Action |
|---------|--------|
| `profile` | Show your current MemSync profile + insights |
| `debug` | Toggle memory retrieval debug output |
| `quit` | Exit (memories persist) |

---

## Programmatic Usage

```python
from chatbot import MemoryChatbot
import asyncio

bot = MemoryChatbot(agent_id="my-app", show_memory_debug=True)

async def main():
    response, payment_hash = await bot.chat(
        "What tech stack should I use for my DeFi project?"
    )
    print(f"Bot: {response}")
    print(f"Proof: {payment_hash}")

    # View stored profile
    profile = bot.get_profile()
    print(profile["user_bio"])

asyncio.run(main())
```

---

## Resources

- [MemSync Full Guide](https://memsync.mintlify.app/)
- [MemSync API Docs](https://api.memchat.io/docs)
- [Register for API key](https://app.memsync.ai/dashboard/api-keys)
