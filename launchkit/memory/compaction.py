"""Keeping one long conversation short: the window, the summary, and what must survive both.

The window is Session 2's num_history_runs: the last 5 turns ride along, older ones drop. A session summary
(enable_session_summaries) replaces what dropped with a model's summary of it, and a summary can leave things out.
must_keep is the hybrid: the rules Maya stated in this conversation, picked out by plain code and re-stated every
turn. A slot until memory hands-on 2, part B builds it.
"""

from agno.db.base import SessionType


def todo(fn):
    """Marks a slot. The harness re-states nothing until it is built."""
    fn.todo = True
    return fn


@todo
def must_keep(said: list[str]) -> list[str]:
    raise NotImplementedError("memory hands-on 2, part B builds this")


def what_she_said(db, session_id: str) -> list[str]:
    """Every message Maya sent in this conversation, oldest first, including the turns the window dropped."""
    session = db.get_session(session_id=session_id, session_type=SessionType.AGENT)
    if session is None:
        return []
    return [str(m.content) for m in session.get_messages() if m.role == "user" and m.content]


def conversation_text(db, session_id: str) -> str:
    """LaunchKit writes its own system message, so Agno's add_session_summary_to_context never reaches the prompt:
    the summary, when there is one, goes in here, with whatever must_keep re-states."""
    session = db.get_session(session_id=session_id, session_type=SessionType.AGENT)
    parts = []
    if session is not None and session.summary is not None:
        parts.append(f"Summary of the earlier turns: {session.summary.summary}")
    if not getattr(must_keep, "todo", False):
        kept = must_keep(what_she_said(db, session_id))
        if kept:
            parts.append("Rules the marketer stated in this conversation; they hold until she says otherwise:\n" + "\n".join(f"- {rule}" for rule in kept))
    return "\n\n".join(parts)
