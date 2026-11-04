"""Reading memory back cheaply: an index in the prompt instead of every row, and a lookup the agent decides to make.

memory_index builds one line per topic in plain code, no model call: the topic, how many facts, and the call that
reads them. recall is a read tool in the catalogue: it returns the full facts for one topic. Both are slots until
memory hands-on 2, part A builds them; until then the prompt carries every row (long_term.memory_text).
"""

from agno.db.schemas.memory import UserMemory

LINE_CAP = 80  # characters per index line, so one long topic name cannot blow out the prompt
INDEX_HEADER = ('Kept from earlier conversations, one line per topic. Before work a topic touches, read it with run_tool("recall", '
                '{"topic": "<topic>"}) and follow it unless this conversation says otherwise. If a fact says to use the brand\'s own '
                "photos and none is attached, ask the marketer for the photo instead of writing a poster.")


def todo(fn):
    """Marks a slot. The harness keeps every row in the prompt until it is built."""
    fn.todo = True
    return fn


@todo
def memory_index(rows: list[UserMemory]) -> str:
    raise NotImplementedError("memory hands-on 2, part A builds this")


@todo
def recall(rows: list[UserMemory], topic: str) -> str:
    raise NotImplementedError("memory hands-on 2, part A builds this")
