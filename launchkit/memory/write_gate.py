"""The policy at the memory table's door: Maya says, in one answer, whether a row is kept and whose it is.

MemoryDb calls ask_before_keeping for every row the memory manager is about to write. It returns "user" (Maya's own),
"workspace" (everyone at the brand), or None (not kept). Session 2's approve(name, inputs) asks her, on the chat page
or in the terminal; an ask that carries choices comes back as the choice she picked, or None if she never answers.
A slot until it is built: until then every row is kept, as Maya's own.
"""

EVERYONE_WARNING = "Everyone at the brand changes the agent for everybody there, not only you."
JUST_ME, EVERYONE, DONT_KEEP = "Just me", "Everyone at the brand", "Don't keep"


def todo(fn):
    """Marks a slot. Nothing calls it until it is built."""
    fn.todo = True
    return fn


@todo
def ask_before_keeping(memory: str, topics: list[str], approve) -> str | None:
    raise NotImplementedError("memory hands-on 1, part 3 builds this")
