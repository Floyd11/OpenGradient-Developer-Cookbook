"""
boilerplates/memsync-chatbot/chatbot.py

Personalized chatbot with persistent memory using MemSync + OpenGradient LLM.
Remembers users across sessions using semantic and episodic memory extraction.

Architecture:
  User message
      │
      ▼
  1. Search MemSync memories ──── POST /memories/search
      │  (relevant past context)
      ▼
  2. Get user profile ──────────── GET /users/profile
      │  (bio + insights)
      ▼
  3. Build enriched system prompt
      │  (memory + profile context)
      ▼
  4. og.LLM.chat() ──────────────── TEE-verified inference
      │  (personalized response + payment_hash)
      ▼
  5. Store conversation ─────────── POST /memories
      │  (MemSync extracts new facts)
      ▼
  Return response to user

Run (interactive REPL):
    python chatbot.py
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests
from dotenv import load_dotenv

import opengradient as og
from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MEMSYNC_BASE_URL: str = "https://api.memchat.io/v1"
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0
DEFAULT_AGENT_ID: str = "memsync-cookbook-bot"
MEMORY_SEARCH_LIMIT: int = 5


# ---------------------------------------------------------------------------
# MemSync API client
# ---------------------------------------------------------------------------
class MemSyncAPI:
    """Thin wrapper around the MemSync REST API."""

    def __init__(self, api_key: str) -> None:
        if not api_key or api_key == "demo_key_placeholder":
            logger.warning("⚠️  MemSync API key not set — memory features disabled")
            self._enabled = False
        else:
            self._enabled = True
        self._headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    @property
    def enabled(self) -> bool:
        return self._enabled

    def store(
        self,
        messages: list[dict],
        agent_id: str,
        thread_id: str,
    ) -> None:
        """Store a conversation for memory extraction."""
        if not self._enabled:
            return
        try:
            resp = requests.post(
                f"{MEMSYNC_BASE_URL}/memories",
                headers=self._headers,
                json={
                    "messages": messages,
                    "agent_id": agent_id,
                    "thread_id": thread_id,
                    "source": "chat",
                },
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"⚠️  Failed to store memories: {e}")

    def search(self, query: str, limit: int = MEMORY_SEARCH_LIMIT) -> dict:
        """Search for memories relevant to a query."""
        if not self._enabled:
            return {"memories": [], "user_bio": ""}
        try:
            resp = requests.post(
                f"{MEMSYNC_BASE_URL}/memories/search",
                headers=self._headers,
                json={"query": query, "limit": limit, "rerank": True},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"⚠️  Memory search failed: {e}")
            return {"memories": [], "user_bio": ""}

    def get_profile(self) -> dict:
        """Get the auto-generated user profile."""
        if not self._enabled:
            return {"user_bio": "", "profiles": [], "insights": []}
        try:
            resp = requests.get(
                f"{MEMSYNC_BASE_URL}/users/profile",
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"⚠️  Profile fetch failed: {e}")
            return {"user_bio": "", "profiles": [], "insights": []}


# ---------------------------------------------------------------------------
# MemoryChatbot
# ---------------------------------------------------------------------------
class MemoryChatbot:
    """
    Personalized chatbot with persistent cross-session memory.

    Memory types stored by MemSync:
      semantic  — lasting facts ("user is a Python developer")
      episodic  — time-bound events ("user mentioned a deadline on March 14")

    The user_bio and memories are injected into the system prompt on every
    turn, giving the LLM rich long-term context beyond its token window.
    """

    def __init__(
        self,
        agent_id: str = DEFAULT_AGENT_ID,
        show_memory_debug: bool = False,
    ) -> None:
        api_key = os.getenv("MEMSYNC_API_KEY", "")
        self._mem = MemSyncAPI(api_key=api_key)
        self._llm = get_llm()
        self._agent_id = agent_id
        self._show_memory_debug = show_memory_debug
        self._approved = False
        self._turn_count = 0

    def _ensure_approval(self) -> None:
        if not self._approved:
            try:
                approval = self._llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
                if approval.tx_hash:
                    logger.info(f"💰 Permit2 tx: {BASESCAN_TX_URL}{approval.tx_hash}")
                self._approved = True
            except Exception as e:
                raise RuntimeError(
                    f"Permit2 OPG approval failed: {e}\n"
                    f"Check your OPG balance at: https://faucet.opengradient.ai"
                ) from e

    def _build_system_prompt(
        self,
        user_bio: str,
        memories: list[dict],
    ) -> str:
        """Construct a personalized system prompt from memory context."""
        base_prompt = (
            "You are a helpful, friendly AI assistant with long-term memory. "
            "You remember past conversations and use that context to give "
            "personalized, relevant responses."
        )
        if not user_bio and not memories:
            return (
                base_prompt + "\n\nThis is the beginning of the conversation. "
                "Be friendly and learn about the user over time."
            )

        context_parts = [base_prompt]

        if user_bio:
            context_parts.append(f"\n\nUser profile:\n{user_bio}")

        if memories:
            mem_lines = "\n".join(
                f"  [{m.get('type', '?')}] {m.get('memory', '')}"
                for m in memories
            )
            context_parts.append(
                f"\n\nRelevant memories from past conversations:\n{mem_lines}"
            )
            context_parts.append(
                "\n\nUse this context naturally — don't list memories explicitly. "
                "Just respond as someone who genuinely remembers the user."
            )

        return "".join(context_parts)

    async def chat(
        self,
        user_message: str,
        thread_id: str | None = None,
    ) -> tuple[str, str]:
        """
        Process a user message and return a memory-enriched response.

        Args:
            user_message: The user's input
            thread_id: Optional conversation thread ID (auto-generated if None)

        Returns:
            Tuple of (response_text, payment_hash)
        """
        self._ensure_approval()
        self._turn_count += 1
        if thread_id is None:
            thread_id = f"thread-{self._agent_id}-{self._turn_count}"

        # 1. Search for relevant memories
        mem_data = self._mem.search(user_message)
        memories = mem_data.get("memories", [])
        user_bio = mem_data.get("user_bio", "")

        if self._show_memory_debug and memories:
            print(f"\n   [Memory: found {len(memories)} relevant memories]")
            for m in memories[:2]:
                print(f"   [{m.get('type', '?')}] {m.get('memory', '')[:80]}")

        # 2. Get user profile for additional context
        if self._turn_count == 1 or self._turn_count % 5 == 0:
            profile = self._mem.get_profile()
            if not user_bio:
                user_bio = profile.get("user_bio", "")

        # 3. Build enriched system prompt
        system_prompt = self._build_system_prompt(user_bio, memories)

        # 4. Run verifiable LLM inference
        try:
            result = await self._llm.chat(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=500,
                temperature=0.4,
            )
            response_text = result.chat_output.get("content", "")
            payment_hash = result.payment_hash
        except Exception as e:
            logger.error(f"❌ LLM inference failed: {e}")
            raise

        # 5. Store the conversation for future memory extraction
        self._mem.store(
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response_text},
            ],
            agent_id=self._agent_id,
            thread_id=thread_id,
        )

        return response_text, payment_hash

    def get_profile(self) -> dict:
        """Retrieve the current user profile from MemSync."""
        return self._mem.get_profile()

    def clear_session(self) -> None:
        """
        Reset turn counter for a fresh session.

        Note: This does NOT delete memories from MemSync — those persist
        across sessions by design. To delete memories, use the MemSync
        dashboard at app.memsync.ai or the DELETE /memories API endpoint.
        """
        self._turn_count = 0
        logger.info("Session reset (memories persist in MemSync)")


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------
async def run_interactive_repl() -> None:
    """Run an interactive chat loop in the terminal."""
    print("\n" + "=" * 60)
    print("🧠 MemSync Chatbot — Personalized AI with Persistent Memory")
    print("=" * 60)

    mem_api_key = os.getenv("MEMSYNC_API_KEY", "")
    if not mem_api_key:
        print("⚠️  MEMSYNC_API_KEY not set — running without memory")
        print("   Register at: https://app.memsync.ai/dashboard/api-keys")
    else:
        print("✅ MemSync connected — memories persist across sessions")

    print("\nCommands:")
    print("  'profile'  — Show your MemSync profile")
    print("  'debug'    — Toggle memory debug output")
    print("  'hashes'   — Toggle payment_hash display")
    print("  'quit'     — Exit")
    print("=" * 60)

    chatbot = MemoryChatbot(show_memory_debug=False)
    show_hashes = False

    print("\nSay hello to get started! (Or type 'quit' to exit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! Your memories are saved in MemSync. 👋")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("Goodbye! Your memories are saved in MemSync. 👋")
            break

        if user_input.lower() == "profile":
            profile = chatbot.get_profile()
            print(f"\n👤 Your Profile:")
            print(f"   Bio     : {profile.get('user_bio', 'Not enough data yet')}")
            insights = profile.get("insights", [])
            if insights:
                print(f"   Insights: {insights[:3]}")
            print()
            continue

        if user_input.lower() == "debug":
            chatbot._show_memory_debug = not chatbot._show_memory_debug
            state = "ON" if chatbot._show_memory_debug else "OFF"
            print(f"   [Memory debug: {state}]\n")
            continue

        if user_input.lower() == "hashes":
            show_hashes = not show_hashes
            state = "ON" if show_hashes else "OFF"
            print(f"   [Payment hash display: {state}]\n")
            continue

        try:
            response, payment_hash = await chatbot.chat(user_input)
            print(f"\nBot: {response}")
            if show_hashes:
                print(f"     [proof: {BASESCAN_TX_URL}{payment_hash}]")
            print()
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(run_interactive_repl())
