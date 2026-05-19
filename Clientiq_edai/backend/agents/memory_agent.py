# Memory agent
"""
ClientIQ — Memory Agent
Manages conversational memory and entity context across turns.
Compresses long conversations and extracts entity focus.
"""

from backend.graph.state import GraphState, AgentMessage
from backend.services.mistral_client import MistralClient
from backend.utils.helpers import utc_now_str
from backend.utils.logger import logger


class MemoryAgent:
    """
    Memory Agent.

    Responsibilities:
    1. Maintain rolling conversation window
    2. Compress old history into a memory summary
    3. Extract current entity context (company / contact)
    4. Inject relevant prior context for next retrieval
    """

    MAX_RAW_TURNS = 6          # keep last 6 turns verbatim
    MAX_SUMMARY_WORDS = 150    # compress older turns to this length

    def __init__(self):
        self.llm = MistralClient()
        self.name = "memory_agent"

    def run(self, state: GraphState) -> GraphState:
        """Update memory and extract entity context."""
        logger.info("[Memory] Processing conversation history ({} turns)", len(state.get("conversation_history", [])))

        history = state.get("conversation_history", [])

        # Add current user turn
        user_turn: AgentMessage = {
            "role": "user",
            "content": state["user_query"],
            "agent": None,
            "timestamp": utc_now_str(),
        }
        history.append(user_turn)

        # Compress if history is long
        if len(history) > self.MAX_RAW_TURNS * 2:
            older = history[:-self.MAX_RAW_TURNS * 2]
            recent = history[-self.MAX_RAW_TURNS * 2:]
            summary = self._compress(older)
            state["memory_summary"] = summary
            state["conversation_history"] = recent
        else:
            # Build simple summary from full history
            state["memory_summary"] = self._build_summary(history)
            state["conversation_history"] = history

        # Extract entity context
        state["entity_context"] = self._extract_entity_context(state["user_query"], state.get("entity_context", {}))

        state["agent_trace"].append(self.name)
        return state

    def _compress(self, old_turns: list) -> str:
        """Use LLM to summarize old conversation turns."""
        turns_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}"
            for t in old_turns
        )
        prompt = f"""Summarize this conversation history in under {self.MAX_SUMMARY_WORDS} words,
preserving key facts, client names, topics discussed, and unresolved questions:

{turns_text}

Summary:"""
        return self.llm.complete(prompt, temperature=0.2)

    def _build_summary(self, history: list) -> str:
        """Build a lightweight summary from recent turns."""
        if not history:
            return ""
        recent = history[-4:]  # last 2 exchanges
        return " | ".join(
            f"{t['role']}: {t['content'][:100]}"
            for t in recent
        )

    def _extract_entity_context(self, query: str, existing: dict) -> dict:
        """
        Extract company/contact entity from the current query.
        Merges with existing context so conversation tracks a single client.
        """
        context = dict(existing)

        # Simple heuristic: look for company name patterns
        import re
        # Quoted names: "Acme Corp" or Acme Corp
        match = re.search(r'"([^"]+)"', query)
        if match:
            context["company_name"] = match.group(1)

        # Keywords suggesting company switch
        if "for " in query.lower():
            after_for = query.lower().split("for ", 1)[-1].split(" ")[0]
            if len(after_for) > 3:
                context["search_hint"] = after_for

        return context
