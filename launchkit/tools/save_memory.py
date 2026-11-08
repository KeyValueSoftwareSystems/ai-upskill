"""Ticket 4: the memory doors. Every write to long-term memory is a catalogue tool of kind "write", so it goes through
run_tool's approval branch from Session 2, like an outside write: the chat shows the planned change and asks first.
Each approved write is logged in the decision log: who allowed what, and when.

save_memory        one note about the person, sorted into rows by the memory manager (ticket 1's rules)
save_learning      one learning for everyone on this brand, stamped with who proposed it (tag source:<user_id>)
search_learnings   reads them back, from this brand's namespace only (ticket 3)
propose_brand_fact a dated brand fact: closes today's row and opens a new one, only after a yes (ticket 3)
"""

import uuid
from datetime import datetime, timezone

from agno.learn.schemas import DecisionLog

from launchkit.knowledge.brand_facts import get_brand_facts, set_brand_fact
from launchkit.memory.long_term import learning_machine, memory_changes, user_memories
from launchkit.memory.scope import held_back
from launchkit.tools.catalogue import Entry


def memory_entries(settings, make_manager, user_id: str, namespace: str = "global") -> list[Entry]:
    """make_manager builds the memory manager when a write is allowed, not before: a turn that saves nothing never loads it."""
    machine = learning_machine(settings, namespace)

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

    def propose_brand_fact(subject: str, value: str) -> str:
        """Propose a new value for one of this brand's dated facts, e.g. the warranty. Shared only after a yes."""
        row = set_brand_fact(settings, namespace, subject.strip().lower(), value.strip(), source=user_id)
        audit(f"set {namespace}'s {row['subject']} to {row['value']} from {row['valid_from']}")
        return f"{namespace}'s {row['subject']} is {row['value']} from {row['valid_from']}; the old value is kept with its end date."

    def current(subject: str) -> str:
        return next((r["value"] for r in get_brand_facts(settings, namespace) if r["subject"] == subject.strip().lower()), "nothing yet")

    def search_learnings(query: str) -> str:
        """Search what the team has learned before."""
        found = machine.learned_knowledge_store.search(query=query, namespace=namespace)
        return "\n".join(f"- {item.title}: {item.learning}" for item in found) or "Nothing learned about that yet."

    return [
        Entry("save_memory", "remember how the marketer likes to work, for later conversations", "write", save_memory,
              plan=lambda i: (f"Not saved: {reason}." + (" Brand facts go in with propose_brand_fact." if "brand fact" in reason else "") if (reason := held_back(i.get("note", ""), settings))
                              else {"store": "user memory", "person": user_id, "note": i.get("note")})),
        Entry("save_learning", "save a learning for everyone who works on this brand", "write", save_learning,
              plan=lambda i: {"store": "learned knowledge", "namespace": namespace, "source": user_id, **i}),
        Entry("search_learnings", "look up what the team has learned before", "read", search_learnings),
        Entry("propose_brand_fact", "change one of this brand's dated facts, such as the warranty, from today", "write", propose_brand_fact,
              plan=lambda i: (f"Not changed: {namespace}'s {i.get('subject')} is already {i.get('value')}." if current(i.get("subject", "")).lower() == str(i.get("value", "")).strip().lower()
                              else {"store": "brand facts", "brand": namespace, "subject": i.get("subject"), "from": current(i.get("subject", "")), "to": i.get("value"), "source": user_id})),
    ]
