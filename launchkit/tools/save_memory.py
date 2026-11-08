"""Ticket 2b: the memory doors. Every write to long-term memory is a catalogue tool of kind "write", so it goes through
run_tool's approval branch from Session 2, like an outside write: the chat shows the planned change and asks first.
Each approved write is logged in the decision log: who allowed what, and when.

save_memory      one note about the person, sorted into rows by the memory manager (ticket 1's rules)
save_learning    one learning for everyone on this brand, stamped with who proposed it (tag source:<user_id>)
search_learnings reads them back
"""

import uuid
from datetime import datetime, timezone

from agno.learn.schemas import DecisionLog

from launchkit.memory.long_term import learning_machine, memory_changes, user_memories
from launchkit.tools.catalogue import Entry


def memory_entries(settings, make_manager, user_id: str, namespace: str = "global") -> list[Entry]:
    """make_manager builds the memory manager when a write is allowed, not before: a turn that saves nothing never loads it."""
    machine = learning_machine(settings)

    def audit(decision: str) -> None:
        machine.decision_log_store.save(DecisionLog(id=uuid.uuid4().hex, decision=decision, reasoning=f"{user_id} allowed it", decision_type="memory_write",
                                                    user_id=user_id, agent_id="launchkit-main", created_at=datetime.now(timezone.utc).isoformat()))

    def save_memory(note: str) -> str:
        """Remember one thing about how the marketer works, for later conversations. The marketer is asked first."""
        manager = make_manager()
        before = user_memories(manager.db, user_id)
        manager.create_user_memories(message=note, user_id=user_id)
        changes = memory_changes(before, user_memories(manager.db, user_id))
        audit(f"saved to {user_id}'s memory: {note}")
        return "; ".join(f"{change}: {text}" for change, text in changes) or "Nothing new to remember."

    def save_learning(title: str, learning: str) -> str:
        """Save one learning for everyone who works on this brand. The marketer is asked first."""
        machine.learned_knowledge_store.save(title=title, learning=learning, tags=[f"source:{user_id}"], agent_id="launchkit-main", namespace=namespace)
        audit(f"saved learning to {namespace}: {title}")
        return f"Saved for everyone on {namespace}: {title}"

    def search_learnings(query: str) -> str:
        """Search what the team has learned before."""
        found = machine.learned_knowledge_store.search(query=query, namespace=namespace)
        return "\n".join(f"- {item.title}: {item.learning}" for item in found) or "Nothing learned about that yet."

    return [
        Entry("save_memory", "remember how the marketer likes to work, for later conversations", "write", save_memory,
              plan=lambda i: {"store": "user memory", "person": user_id, "note": i.get("note")}),
        Entry("save_learning", "save a learning for everyone who works on this brand", "write", save_learning,
              plan=lambda i: {"store": "learned knowledge", "namespace": namespace, "source": user_id, **i}),
        Entry("search_learnings", "look up what the team has learned before", "read", search_learnings),
    ]
