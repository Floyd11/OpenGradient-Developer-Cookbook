"""
schemas.py — Pydantic v2 request/response models for the FastAPI backend.
"""

from typing import Literal
from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    """Request body for the /infer endpoint (text completion)."""
    prompt: str = Field(..., description="Text prompt to send to the LLM")
    model: str = Field(
        default="gpt-5",
        description="Model identifier. Options: gpt-5, gpt-5-mini, claude-sonnet-4-6, gemini-2.5-flash, grok-4",
    )
    max_tokens: int = Field(default=500, ge=1, le=4096, description="Max tokens to generate")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature")
    settlement_mode: Literal["private", "individual_full", "batch_hashed"] = Field(
        default="batch_hashed",
        description="x402 settlement mode: privacy vs auditability tradeoff",
    )


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: Literal["system", "user", "assistant", "tool"] = Field(
        ..., description="Message role"
    )
    content: str = Field(..., description="Message content")
    name: str | None = Field(default=None, description="Optional name for the message author")


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    messages: list[ChatMessage] = Field(
        ..., description="Conversation history", min_length=1
    )
    model: str = Field(default="gpt-5")
    max_tokens: int = Field(default=500, ge=1, le=4096)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    tools: list[dict] | None = Field(
        default=None,
        description="Optional tool/function definitions (OpenAI-compatible schema)",
    )
    settlement_mode: Literal["private", "individual_full", "batch_hashed"] = Field(
        default="batch_hashed"
    )


class InferenceResponse(BaseModel):
    """Successful inference response with verifiable proof."""
    response: str = Field(..., description="LLM response text")
    payment_hash: str = Field(
        ..., description="TEE verification payment hash — your on-chain proof"
    )
    basescan_url: str = Field(..., description="Direct link to verify on Basescan")
    model_used: str = Field(..., description="The model that generated the response")
    settlement_mode: str = Field(..., description="Settlement mode used")
    tool_calls: list[dict] | None = Field(
        default=None, description="Tool calls requested by the model (if any)"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    network: str
    permit2_approved: bool
    og_explorer: str


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Detailed error message")
