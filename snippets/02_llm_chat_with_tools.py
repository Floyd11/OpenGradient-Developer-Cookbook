"""
snippets/02_llm_chat_with_tools.py — Multi-Turn Chat with Tool/Function Calling

Demonstrates the most advanced LLM pattern: defining tools (functions) that the
model can decide to call, receiving structured tool_call results, and continuing
the conversation. All reasoning steps are TEE-verified.

This is the foundation for building AI agents that interact with external APIs,
databases, or on-chain contracts.

When to use this pattern:
  - Building agents that need to fetch live data (weather, prices, blockchain state)
  - Any workflow where the LLM must make structured decisions about external actions
  - When you need OpenAI-compatible function calling with verifiable proof

Run:
    python snippets/02_llm_chat_with_tools.py
"""

import asyncio
import json
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
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0

# ---------------------------------------------------------------------------
# Tool Definitions — OpenAI-compatible JSON schema format
# ---------------------------------------------------------------------------
TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": (
                "Get the current weather conditions for a given city and state. "
                "Use this when the user asks about weather in any location."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g. 'San Francisco'",
                    },
                    "state": {
                        "type": "string",
                        "description": (
                            "The two-letter US state abbreviation, e.g. 'CA' for California"
                        ),
                    },
                    "unit": {
                        "type": "string",
                        "description": "Temperature unit to use for the response",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["city", "state", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_opg_token_price",
            "description": "Get the current price of the $OPG token in USD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "The currency to express the price in",
                        "enum": ["USD", "ETH", "BTC"],
                    }
                },
                "required": ["currency"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Simulated tool execution (replace with real implementations in production)
# ---------------------------------------------------------------------------
def execute_tool(tool_name: str, tool_args: dict) -> str:
    """
    Execute a tool call and return the result as a string.

    In production, replace each branch with a real API call:
    - get_current_weather -> call a weather API (e.g., OpenWeatherMap)
    - get_opg_token_price -> call CoinGecko or a DEX price feed
    """
    logger.info(f"🔧 Executing tool: {tool_name}({json.dumps(tool_args)})")

    if tool_name == "get_current_weather":
        # TODO: Replace with real weather API call
        return json.dumps({
            "city": tool_args.get("city"),
            "state": tool_args.get("state"),
            "temperature": 72,
            "unit": tool_args.get("unit", "fahrenheit"),
            "condition": "Partly cloudy",
            "humidity": "58%",
        })
    elif tool_name == "get_opg_token_price":
        # TODO: Replace with real price feed (CoinGecko, DEX, etc.)
        return json.dumps({
            "token": "OPG",
            "price": 0.042,
            "currency": tool_args.get("currency", "USD"),
            "source": "mock_price_feed",
        })
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def run_chat_with_tools() -> None:
    """Demonstrate a multi-turn chat conversation with tool calling."""
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

    # Conversation history
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                "Use the provided tools to answer questions about weather and crypto prices. "
                "Always use tools when they are relevant rather than guessing."
            ),
        },
        {
            "role": "user",
            "content": (
                "What's the weather like in Dallas, Texas right now? "
                "Also, what's the current price of the OPG token in USD?"
            ),
        },
    ]

    print("\n" + "=" * 60)
    print("💬 Chat with Tool Calling — Starting conversation")
    print("=" * 60)
    print(f"👤 User: {messages[-1]['content']}\n")

    # Step 1: Initial chat request — model may respond with tool_calls
    logger.info(f"🤖 Sending to {DEFAULT_MODEL.value} with {len(TOOLS)} tools available...")
    try:
        result = await llm.chat(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=TOOLS,
            # tool_choice options:
            #   "auto"     — model decides whether to call a tool (default)
            #   "none"     — model must NOT call any tool
            #   "required" — model MUST call at least one tool
            tool_choice="auto",
            max_tokens=500,
            temperature=0.0,
        )
    except Exception as e:
        logger.error(f"❌ Chat inference failed: {e}")
        raise

    response_content = result.chat_output.get("content", "")
    tool_calls = result.chat_output.get("tool_calls", [])

    print(f"🤖 Assistant (initial): {response_content or '[requesting tool calls]'}")
    if tool_calls:
        print(f"\n🔧 Tool calls requested: {len(tool_calls)}")

    # Step 2: Execute tool calls and feed results back into the conversation
    if tool_calls:
        # Add assistant's response (with tool_calls) to message history
        messages.append({
            "role": "assistant",
            "content": response_content,
            "tool_calls": tool_calls,
        })

        # Execute each tool and add results
        for tc in tool_calls:
            fn_name: str = tc["function"]["name"]
            fn_args: dict = json.loads(tc["function"]["arguments"])
            tool_result: str = execute_tool(fn_name, fn_args)

            print(f"  ↳ {fn_name}({fn_args}) → {tool_result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": fn_name,
                "content": tool_result,
            })

        # Step 3: Second call — model synthesizes tool results into final answer
        logger.info("🤖 Sending tool results back for final synthesis...")
        try:
            final_result = await llm.chat(
                model=DEFAULT_MODEL,
                messages=messages,
                max_tokens=500,
                temperature=0.0,
            )
        except Exception as e:
            logger.error(f"❌ Final synthesis failed: {e}")
            raise

        final_response = final_result.chat_output.get("content", "")
        print(f"\n🤖 Assistant (final): {final_response}")
        print(f"\n💰 Payment Hash (synthesis): {BASESCAN_TX_URL}{final_result.payment_hash}")
    else:
        print(f"\n🤖 Assistant: {response_content}")

    print(f"\n💰 Payment Hash (initial): {BASESCAN_TX_URL}{result.payment_hash}")
    print("=" * 60)
    print(
        "\nℹ️  Each payment_hash proves the model processed these messages\n"
        "   inside a TEE — including your tool schemas and results.\n"
        "   This means the entire reasoning chain is cryptographically auditable."
    )


if __name__ == "__main__":
    asyncio.run(run_chat_with_tools())
