"""The write door: who decides that a fact is worth keeping.

Slot for build B, ticket 4, and the first fork. Reference: page 3, "Formation".

`MemoryStore` calls `decide_save` for every row before it reaches the table. The participant chooses
how the door works:

  Path A, ask first: the agent proposes the row, the person answers "Just me", "Everyone at the brand"
  or "Don't keep", through the same approval rule Session 2 used for writes. `approve(name, inputs)`
  shows the question on the chat page when `inputs` has a `choices` list, and returns the chosen text.

  Path B, save when sure: `confidence(text, settings)` asks a small model how sure it is that the row is
  a lasting fact about the person, 0 to 1. At 0.7 or more the row is kept and the Memory panel shows
  it with a Forget button; below that it is not kept. Nobody is asked.

Either way, a row whose source is a web page (`source:web`) is refused: a page the helper read can say
anything, and a saved row outlives the page.

The placeholder keeps every row and asks nobody. That is how memory shipped.
"""

from __future__ import annotations

from collections.abc import Callable

from launchkit.memory.store import Decision

CONFIDENCE_GATE = 0.7


CONFIDENCE_ASK = (
    "A marketing assistant is deciding whether to remember this about the person it works for:\n\n{text}\n\n"
    "How sure are you that this is a lasting fact about the person, true next month, and worth keeping? "
    "Answer with one number from 0 to 1 and nothing else."
)


def confidence(text: str, settings, trace=None) -> float:
    """How sure a small model is that `text` is a lasting fact about the person, from 0 to 1.

    One short call on the memory_write job's model, billed to the run's trace when one is given. A reply
    that is not a number, or a call that fails, counts as 0, so a broken call never saves anything.
    """
    import re

    from agno.exceptions import ModelProviderError
    from agno.models.message import Message

    from launchkit.adapters.jobs import Jobs
    from launchkit.trace import Trace

    model = Jobs(settings, trace or Trace()).first("memory_write")
    try:
        answer = model.response(messages=[Message(role="user", content=CONFIDENCE_ASK.format(text=text))])
    except ModelProviderError:
        return 0.0
    found = re.search(r"(?:0?\.\d+|1(?:\.0+)?|0)", str(answer.content or ""))
    return min(max(float(found.group()), 0.0), 1.0) if found else 0.0


def decide_save(text: str, topics: list[str], approve: Callable[[str, dict], object], settings, trace=None) -> Decision:
    """Keep this row or not, and under which scope.

    `text` is the row as the extractor or the agent worded it. `topics` are the labels the door has
    stamped so far (kind, author, source, scope, valid_from). `approve` is the chat page's question
    box: pass it a name and inputs; with `choices` in inputs it returns the chosen text. `trace` is the
    run's trace, so a model call made here lands on the scoreboard.
    """
    if "source:web" in topics:
        # A page the helper read can say anything, and a saved row outlives the page.
        return Decision(keep=False, scope=None)
    # Path B: nobody is asked. The row is kept when the model is sure enough, and the Memory panel shows it
    # with Forget, so the person can undo it.
    return Decision(keep=confidence(text, settings, trace) >= CONFIDENCE_GATE, scope=None)
