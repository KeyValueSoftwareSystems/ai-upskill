"""The policy at the memory table's door: Maya says yes before a row is kept, and says whose it is.

MemoryDb calls ask_before_keeping for every row the memory manager is about to write. It returns "user" (Maya's own),
"workspace" (everyone at the brand), or None (not kept). Session 2's approve(name, inputs) asks her, on the chat page
or in the terminal. A slot until it is built: until then every row is kept, as Maya's own.
"""


def todo(fn):
    """Marks a slot. Nothing calls it until it is built."""
    fn.todo = True
    return fn


@todo
def ask_before_keeping(memory: str, topics: list[str], approve) -> str | None:
    raise NotImplementedError("memory hands-on 1, part 3 builds this")
