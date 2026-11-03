"""Reading memory back cheaply: an index in the prompt instead of every row, and a lookup the agent decides to make.

memory_index builds one line per topic in plain code, no model call. recall is a read tool in the catalogue: it
returns the full facts for one topic. Both are slots until memory step 3 builds them; until then the prompt carries
every row (long_term.memory_text).
"""

from agno.db.schemas.memory import UserMemory

LINE_CAP = 120  # characters per index line, so one long fact cannot blow out the prompt


def todo(fn):
    """Marks a slot. The harness keeps every row in the prompt until it is built."""
    fn.todo = True
    return fn


@todo
def memory_index(rows: list[UserMemory]) -> str:
    raise NotImplementedError("memory step 3 builds this")


@todo
def recall(rows: list[UserMemory], topic: str) -> str:
    raise NotImplementedError("memory step 3 builds this")
