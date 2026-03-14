"""
snippets/07_memsync_personalized_bot.py — MemSync: Persistent AI Memory

Demonstrates the full MemSync integration:
  1. Store a conversation (MemSync extracts facts automatically)
  2. Search for relevant memories given a new query
  3. Retrieve the auto-generated user profile
  4. Build a personalized chatbot that injects memory context into prompts

How MemSync Works:
  - You POST conversation messages → MemSync's LLM (powered by OpenGradient TEE)
    automatically extracts facts and stores them as memories
  - Memories are typed as:
      "semantic"  — lasting facts ("user is a software engineer")
      "episodic"  — time-bound events ("user mentioned a project on March 14")
  - On the next conversation turn, you search for relevant memories and inject
    them into the system prompt — giving the LLM long-term context beyond its
    token window

API Endpoints:
  Base URL: https://api.memchat.io/v1
  Auth: X-API-Key header

Run:
    python snippets/07_memsync_personalized_bot.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv

import opengradient as og
from utils.client import get_llm, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MEMSYNC_BASE_URL: str = "https://api.memchat.io/v1"
AGENT_ID: str = "cookbook-demo-bot"
THREAD_ID: str = "demo-thread-001"
DEFAULT_MODEL: og.TEE_LLM = og.TEE_LLM.GPT_5
BASESCAN_TX_URL: str = "https://sepolia.basescan.org/tx/"
OPG_APPROVAL_AMOUNT: float = 5.0


class MemSyncClient:
    """Minimal wrapper around the MemSync REST API."""

    def __init__(self, api_key: str) -> None:
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    def store_conversation(
        self,
        messages: list[dict],
        thread_id: str = THREAD_ID,
        agent_id: str = AGENT_ID,
    ) -> dict:
        """
        Store a conversation so MemSync can extract memories from it.
        """
        resp = requests.post(
            f"{MEMSYNC_BASE_URL}/memories",
            headers=self.headers,
            json={
                "messages": messages,
                "agent_id": agent_id,
                "thread_id": thread_id,
                "source": "chat",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def search_memories(self, query: str, limit: int = 5) -> dict:
        """
        Search for memories relevant to a query.
        """
        resp = requests.post(
            f"{MEMSYNC_BASE_URL}/memories/search",
            headers=self.headers,
            json={"query": query, "limit": limit, "rerank": True},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_profile(self) -> dict:
        """
        Retrieve the user's auto-generated profile.
        """
        resp = requests.get(
            f"{MEMSYNC_BASE_URL}/users/profile",
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


class PersonalizedChatbot:
    """
    A chatbot that uses MemSync for persistent memory and OpenGradient LLM
    for verifiable, TEE-backed inference.
    """

    def __init__(self, memsync_api_key: str) -> None:
        self.mem = MemSyncClient(api_key=memsync_api_key)
        self.llm = get_llm()
        self._approved = False

    def _ensure_approval(self) -> None:
        """Ensure Permit2 OPG allowance (called once)."""
        if not self._approved:
            approval = self.llm.ensure_opg_approval(opg_amount=OPG_APPROVAL_AMOUNT)
            if approval.tx_hash:
                logger.info(f"💰 Permit2 tx: {BASESCAN_TX_URL}{approval.tx_hash}")
            self._approved = True

    async def chat(self, user_message: str, thread_id: str = THREAD_ID) -> tuple[str, str]:
        """
        Process a user message with memory-enriched context.
        """
        self._ensure_approval()

        # 1. Search for relevant memories
        logger.info(f"🔍 Searching memories for: '{user_message[:50]}...'")
        try:
            memory_data = self.mem.search_memories(query=user_message, limit=5)
            memories = memory_data.get("memories", [])
            user_bio = memory_data.get("user_bio", "")
        except requests.RequestException as e:
            logger.warning(f"⚠️ Memory search failed: {e} — continuing without memory")
            memories = []
            user_bio = ""

        # 2. Build enriched system prompt with memory context
        memory_context = ""
        if memories:
            memory_lines = "\n".join(
                f"  - [{m.get('type', 'unknown')}] {m.get('memory', '')}"
                for m in memories
            )
            memory_context = f"\n\nRelevant memories about this user:\n{memory_lines}"

        bio_context = f"\nUser summary: {user_bio}" if user_bio else ""

        system_prompt = (
            "You are a helpful, personalized AI assistant. "
            "Use the context below to give relevant, personalized responses."
            f"{bio_context}"
            f"{memory_context}"
            "\n\nIf no memory context is available, respond helpfully and ask "
            "clarifying questions to learn about the user."
        )

        # 3. Call OpenGradient LLM (verifiable TEE inference)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        try:
            result = await self.llm.chat(
                model=DEFAULT_MODEL,
                messages=messages,
                max_tokens=400,
                temperature=0.3,
            )
            response_text = result.chat_output.get("content", "")
            payment_hash = result.payment_hash
        except Exception as e:
            logger.error(f"❌ LLM inference failed: {e}")
            raise

        # 4. Store the conversation for future memory extraction
        try:
            self.mem.store_conversation(
                messages=[
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": response_text},
                ],
                thread_id=thread_id,
            )
            logger.info("✅ Conversation stored in MemSync")
        except requests.RequestException as e:
            logger.warning(f"⚠️ Failed to store conversation: {e}")

        return response_text, payment_hash


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
async def run_memsync_demo() -> None:
    """Demonstrate the full MemSync + OpenGradient pipeline."""
    api_key = os.getenv("MEMSYNC_API_KEY")
    if not api_key:
        print("⚠️  MEMSYNC_API_KEY not set in .env")
        print("   Register at: https://app.memsync.ai/dashboard/api-keys")
        print("   Running in demo mode (memory features skipped)...")
        api_key = "demo_key_placeholder"

    mem = MemSyncClient(api_key=api_key)
    bot = PersonalizedChatbot(memsync_api_key=api_key)

    print("\n" + "=" * 60)
    print("🧠 MemSync + OpenGradient — Personalized AI Demo")
    print("=" * 60)

    # Step 1: Seed some initial memories
    print("\n📝 Step 1: Seeding initial memories...")
    seed_messages = [
        {
            "role": "user",
            "content": (
                "Hi! I'm a blockchain developer at a DeFi startup. "
                "I work mainly with Solidity and Python. "
                "My biggest project is building a verifiable AI oracle system."
            ),
        },
        {
            "role": "assistant",
            "content": (
                "That sounds fascinating! Verifiable AI oracles are a cutting-edge area. "
                "OpenGradient's TEE infrastructure would be perfect for that use case."
            ),
        },
    ]
    try:
        mem.store_conversation(messages=seed_messages)
        print("✅ Memories seeded successfully")
    except requests.RequestException as e:
        print(f"⚠️  Could not seed memories (API key may be invalid): {e}")

    # Step 2: Search memories
    print("\n🔍 Step 2: Searching for relevant memories...")
    try:
        results = mem.search_memories("What does the user work on?")
        print(f"✅ User Bio: {results.get('user_bio', 'N/A')}")
        print(f"   Found {len(results.get('memories', []))} memories:")
        for m in results.get("memories", [])[:3]:
            print(f"     [{m.get('type', '?')}] {m.get('memory', '')} "
                  f"(score: {m.get('rerank_score', 0):.2f})")
    except requests.RequestException as e:
        print(f"⚠️  Memory search failed: {e}")

    # Step 3: Get user profile
    print("\n👤 Step 3: Fetching user profile...")
    try:
        profile = mem.get_profile()
        print(f"✅ Bio: {profile.get('user_bio', 'N/A')}")
        insights = profile.get("insights", [])
        if insights:
            print(f"   Insights: {insights[:2]}")
    except requests.RequestException as e:
        print(f"⚠️  Profile fetch failed: {e}")

    # Step 4: Run a personalized chat turn
    print("\n💬 Step 4: Running personalized chat...")
    user_msg = "What OpenGradient features would be most useful for my project?"
    print(f"👤 User: {user_msg}")

    try:
        response, payment_hash = await bot.chat(user_msg)
        print(f"🤖 Assistant: {response}")
        print(f"\n💰 Payment Hash: {payment_hash}")
        print(f"🔗 {BASESCAN_TX_URL}{payment_hash}")
    except Exception as e:
        print(f"❌ Chat failed: {e}")

    print("\n" + "=" * 60)
    print("✅ MemSync demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_memsync_demo())
