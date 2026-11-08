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


def confidence(text: str, settings, trace=None) -> float:
    """How sure a small model is that `text` is a lasting fact about the person, from 0 to 1.

    Path B builds this. It is one short model call; the fake models answer it the same way every time.
    """
    raise NotImplementedError("path B of the first fork builds confidence()")


def decide_save(text: str, topics: list[str], approve: Callable[[str, dict], object], settings, trace=None) -> Decision:
    """Keep this row or not, and under which scope.

    `text` is the row as the extractor or the agent worded it. `topics` are the labels the door has
    stamped so far (kind, author, source, scope, valid_from). `approve` is the chat page's question
    box: pass it a name and inputs; with `choices` in inputs it returns the chosen text. `trace` is the
    run's trace, so a model call made here lands on the scoreboard.
    """
    return Decision(keep=True, scope=None)
