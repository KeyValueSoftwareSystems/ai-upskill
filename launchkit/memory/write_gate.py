"""The policy at the memory table's door: Maya says, in one answer, whether a row is kept and whose it is.

MemoryDb calls ask_before_keeping for every row the memory manager is about to write. It returns "user" (Maya's own),
"workspace" (everyone at the brand), or None (not kept). Session 2's approve(name, inputs) asks her, on the chat page
or in the terminal; an ask that carries choices comes back as the choice she picked, or None if she never answers.
"""

EVERYONE_WARNING = "Everyone at the brand changes the agent for everybody there, not only you."
JUST_ME, EVERYONE, DONT_KEEP = "Just me", "Everyone at the brand", "Don't keep"
SCOPES = {JUST_ME: "user", EVERYONE: "workspace"}


def ask_before_keeping(memory: str, topics: list[str], approve) -> str | None:
    from launchkit.memory.long_term import KINDS  # long_term imports this module, so KINDS is read at call time

    kind = next((t for t in topics if t in KINDS), "")
    answer = approve("keep_in_memory", {"memory": memory, "kind": kind, "warning": EVERYONE_WARNING,
                                        "choices": [JUST_ME, EVERYONE, DONT_KEEP]})
    return SCOPES.get(answer)
