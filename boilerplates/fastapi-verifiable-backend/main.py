"""
boilerplates/fastapi-verifiable-backend/main.py

Production-ready FastAPI server exposing OpenGradient verifiable LLM inference
as a REST API. Every AI response includes a payment_hash — cryptographic proof
the inference ran inside a TEE (Trusted Execution Environment).

Endpoints:
  GET  /health  — Health check + Permit2 approval status
  POST /infer   — Text completion with verifiable proof
  POST /chat    — Multi-turn chat with optional tool calling
  POST /stream  — Streaming chat via Server-Sent Events (SSE)

Run:
  uvicorn main:app --reload --host 0.0.0.0 --port 8000

Then visit: http://localhost:8000/docs
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

import opengradient as og
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from schemas import (
    ChatRequest,
    ErrorResponse,
    HealthResponse,
    InferenceRequest,
    InferenceResponse,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("og.fastapi")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OG_EXPLORER_URL: str = "https://explorer.opengradient.ai"
OPG_APPROVAL_AMOUNT: float = 5.0

# Model name → og.TEE_LLM mapping
MODEL_MAP: dict[str, og.TEE_LLM] = {
    "gpt-5":               og.TEE_LLM.GPT_5,
    "gpt-5-mini":          og.TEE_LLM.GPT_5_MINI,
    "gpt-4.1":             og.TEE_LLM.GPT_4_1_2025_04_14,
    "o4-mini":             og.TEE_LLM.O4_MINI,
    "claude-opus-4-6":     og.TEE_LLM.CLAUDE_OPUS_4_6,
    "claude-sonnet-4-6":   og.TEE_LLM.CLAUDE_SONNET_4_6,
    "claude-haiku-4-5":    og.TEE_LLM.CLAUDE_HAIKU_4_5,
    "gemini-3-pro":        og.TEE_LLM.GEMINI_3_PRO,
    "gemini-2.5-pro":      og.TEE_LLM.GEMINI_2_5_PRO,
    "gemini-2.5-flash":    og.TEE_LLM.GEMINI_2_5_FLASH,
    "grok-4":              og.TEE_LLM.GROK_4,
    "grok-4-fast":         og.TEE_LLM.GROK_4_FAST,
}

SETTLEMENT_MAP: dict[str, og.x402SettlementMode] = {
    "private":         og.x402SettlementMode.PRIVATE,
    "individual_full": og.x402SettlementMode.INDIVIDUAL_FULL,
    "batch_hashed":    og.x402SettlementMode.BATCH_HASHED,
}

# ---------------------------------------------------------------------------
# Global LLM state
# ---------------------------------------------------------------------------
_llm: og.LLM | None = None
_permit2_approved: bool = False


def get_llm() -> og.LLM:
    # NOTE: FastAPI manages its own og.LLM singleton here rather than using
    # utils/client.py because a web server needs a module-level instance
    # that survives across requests within the same process. The utils module
    # is designed for script-level use; both patterns are correct.
    global _llm
    if _llm is None:
        private_key = os.getenv("OG_PRIVATE_KEY")
        if not private_key:
            raise RuntimeError("OG_PRIVATE_KEY not configured")
        _llm = og.LLM(private_key=private_key)
    return _llm


def resolve_model(model_name: str) -> og.TEE_LLM:
    """Resolve a string model name to an og.TEE_LLM enum value."""
    model = MODEL_MAP.get(model_name.lower())
    if model is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model_name}'. Available: {list(MODEL_MAP.keys())}",
        )
    return model


def resolve_settlement(mode_name: str) -> og.x402SettlementMode:
    """Resolve a string settlement mode to an og.x402SettlementMode enum value."""
    mode = SETTLEMENT_MAP.get(mode_name.lower())
    if mode is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown settlement mode '{mode_name}'. Available: {list(SETTLEMENT_MAP.keys())}",
        )
    return mode


# ---------------------------------------------------------------------------
# Lifespan — startup + shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize LLM and ensure Permit2 approval."""
    global _permit2_approved
    logger.info("🚀 Starting OpenGradient FastAPI backend...")

    try:
        llm = get_llm()
        logger.info("✅ og.LLM initialized")

        # Ensure Permit2 allowance once at startup
        approval = llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
        _permit2_approved = True

        if approval.tx_hash:
            logger.info(f"💰 Permit2 approval tx: {BASESCAN_TX_URL}{approval.tx_hash}")
        else:
            logger.info("💰 Permit2 allowance already sufficient")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        logger.warning("Server will start but inference may fail — check your .env")

    yield  # Server runs here

    logger.info("🛑 Shutting down OpenGradient FastAPI backend")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="OpenGradient Verifiable AI Backend",
    description=(
        "REST API for verifiable LLM inference powered by OpenGradient's x402 Gateway. "
        "Every response includes a payment_hash — cryptographic proof that the AI "
        "inference ran inside a Trusted Execution Environment (TEE)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow all origins for development
# In production, restrict to your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, and duration for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} "
        f"({duration_ms:.1f}ms)"
    )
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns server status and Permit2 approval state.",
)
async def health_check() -> HealthResponse:
    """Check server health and OPG Permit2 approval status."""
    return HealthResponse(
        status="ok",
        network="base-sepolia",
        permit2_approved=_permit2_approved,
        og_explorer=OG_EXPLORER_URL,
    )


@app.post(
    "/infer",
    response_model=InferenceResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Text Completion",
    description=(
        "Run a verifiable text completion via OpenGradient's x402 Gateway. "
        "Returns the response text plus a payment_hash for on-chain verification."
    ),
)
async def infer(request: InferenceRequest) -> InferenceResponse:
    """
    Execute a verifiable LLM text completion.

    Returns:
        InferenceResponse with response text, payment_hash, and Basescan URL
    """
    llm = get_llm()
    model = resolve_model(request.model)
    settlement = resolve_settlement(request.settlement_mode)

    logger.info(f"🤖 /infer — model={request.model}, settlement={request.settlement_mode}")

    try:
        result = await llm.completion(
            model=model,
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            x402_settlement_mode=settlement,
        )
    except Exception as e:
        logger.error(f"❌ Inference failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="inference_failed",
                detail=str(e),
            ).model_dump(),
        )

    return InferenceResponse(
        response=result.completion_output,
        payment_hash=result.payment_hash,
        basescan_url=f"{BASESCAN_TX_URL}{result.payment_hash}",
        model_used=request.model,
        settlement_mode=request.settlement_mode,
    )


@app.post(
    "/chat",
    response_model=InferenceResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Chat Completion",
    description=(
        "Run a verifiable multi-turn chat completion with optional tool calling. "
        "Returns the assistant's response plus a payment_hash."
    ),
)
async def chat(request: ChatRequest) -> InferenceResponse:
    """
    Execute a verifiable LLM chat completion.

    Supports:
    - Multi-turn conversation history
    - Optional tool/function calling (OpenAI-compatible schema)
    - All three settlement modes

    Returns:
        InferenceResponse with response, tool_calls (if any), and payment_hash
    """
    llm = get_llm()
    model = resolve_model(request.model)
    settlement = resolve_settlement(request.settlement_mode)

    messages = [m.model_dump(exclude_none=True) for m in request.messages]
    logger.info(
        f"💬 /chat — model={request.model}, messages={len(messages)}, "
        f"tools={len(request.tools or [])}, settlement={request.settlement_mode}"
    )

    try:
        result = await llm.chat(
            model=model,
            messages=messages,
            tools=request.tools,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            x402_settlement_mode=settlement,
        )
    except Exception as e:
        logger.error(f"❌ Chat inference failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="chat_failed",
                detail=str(e),
            ).model_dump(),
        )

    response_content = result.chat_output.get("content", "")
    tool_calls = result.chat_output.get("tool_calls")

    return InferenceResponse(
        response=response_content or "",
        payment_hash=result.payment_hash,
        basescan_url=f"{BASESCAN_TX_URL}{result.payment_hash}",
        model_used=request.model,
        settlement_mode=request.settlement_mode,
        tool_calls=tool_calls,
    )


@app.post(
    "/stream",
    summary="Streaming Chat",
    description=(
        "Stream a verifiable chat response via Server-Sent Events (SSE). "
        "Tokens are sent as they are generated."
    ),
)
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    """
    Stream a verifiable LLM chat response via SSE.

    Frontend integration:
        const eventSource = new EventSource('/stream');
        eventSource.onmessage = (e) => console.log(e.data);

    Returns:
        StreamingResponse with SSE format: "data: <token>\\n\\n"
    """
    llm = get_llm()
    model = resolve_model(request.model)
    messages = [m.model_dump(exclude_none=True) for m in request.messages]

    logger.info(f"📡 /stream — model={request.model}")

    async def event_generator():
        try:
            stream = await llm.chat(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    # SSE format: data: <content>\n\n
                    yield f"data: {delta.content}\n\n"
        except Exception as e:
            logger.error(f"❌ Stream error: {e}")
            yield f"data: [ERROR] {e}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering for SSE
        },
    )
