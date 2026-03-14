"""
snippets/03_llm_streaming.py — Real-Time Streaming Chat

Demonstrates streaming LLM responses for terminal applications and web UIs.
Instead of waiting for the full response, tokens are printed as they arrive,
providing a much better user experience for longer outputs.

When to use streaming:
  - Terminal chat interfaces where you want typewriter-style output
  - Web applications sending Server-Sent Events (SSE) to the frontend
  - Any UX where latency perception matters more than total throughput

TODO (web integration):
  - For FastAPI SSE: yield each chunk inside a StreamingResponse with
    media_type="text/event-stream"
  - For WebSocket: send each chunk.choices[0].delta.content via ws.send()

Run:
    python snippets/03_llm_streaming.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import opengradient as og
from dotenv import load_dotenv

from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_4_1_2025_04_14
MAX_TOKENS: int = 400
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0

# Multi-turn conversation to stream
MESSAGES: list[dict] = [
    {
        "role": "user",
        "content": "What is Python? Give a clear 3-paragraph explanation.",
    },
    {
        "role": "assistant",
        "content": "Python is a high-level, interpreted programming language known for its simplicity.",
    },
    {
        "role": "user",
        "content": "Great! Now explain what makes it especially good for AI and machine learning work.",
    },
]


# ---------------------------------------------------------------------------
# Streaming handler
# ---------------------------------------------------------------------------
async def stream_response() -> None:
    """Stream an LLM response token-by-token and print in real-time."""
    llm = get_llm()

    # Ensure Permit2 allowance
    logger.info("Checking Permit2 $OPG allowance...")
    try:
        approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
        if approval.tx_hash:
            logger.info(f"💰 Permit2 approval tx: {BASESCAN_TX_URL}{approval.tx_hash}")
    except Exception as e:
        logger.error(f"❌ Permit2 approval failed: {e}")
        raise

    print("\n" + "=" * 60)
    print(f"🤖 Streaming from {DEFAULT_MODEL.value}")
    print("=" * 60)
    print(f"👤 User: {MESSAGES[-1]['content']}\n")
    print("🤖 Assistant (streaming): ", end="", flush=True)

    # Request streaming response — returns an AsyncGenerator of StreamChunk
    try:
        stream = await llm.chat(
            model=DEFAULT_MODEL,
            messages=MESSAGES,
            stream=True,       # <-- enables streaming mode
            max_tokens=MAX_TOKENS,
            temperature=0.3,
        )
    except Exception as e:
        logger.error(f"❌ Failed to initiate stream: {e}")
        raise

    # Consume the stream chunk by chunk
    collected_content: list[str] = []
    try:
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                print(delta.content, end="", flush=True)
                collected_content.append(delta.content)
    except Exception as e:
        logger.error(f"❌ Stream interrupted: {e}")
        raise

    full_response = "".join(collected_content)
    print("\n")  # newline after stream ends

    print("=" * 60)
    print(f"✅ Stream complete — {len(full_response)} characters received")
    print("=" * 60)

    # TODO (FastAPI SSE integration):
    # @app.get("/stream")
    # async def stream_endpoint(prompt: str):
    #     async def event_generator():
    #         stream = await llm.chat(model=..., messages=[...], stream=True)
    #         async for chunk in stream:
    #             content = chunk.choices[0].delta.content
    #             if content:
    #                 yield f"data: {content}\n\n"
    #     return StreamingResponse(event_generator(), media_type="text/event-stream")

    # TODO (WebSocket integration):
    # async for chunk in stream:
    #     await websocket.send_text(chunk.choices[0].delta.content or "")


if __name__ == "__main__":
    asyncio.run(stream_response())
