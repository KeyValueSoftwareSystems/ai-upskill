"""Reading memory back cheaply: an index in the prompt instead of every row, and a lookup the agent decides to make.

memory_index builds one line per topic in plain code, no model call: the topic, how many facts, and the call that
reads them. recall is a read tool in the catalogue: it returns the full facts for one topic. Both are slots until
memory hands-on 2, part A builds them; until then the prompt carries every row (long_term.memory_text).
"""

from agno.db.schemas.memory import UserMemory

from launchkit.memory.long_term import kind_of, topic_of

LINE_CAP = 80  # characters per index line, so one long topic name cannot blow out the prompt
INDEX_HEADER = ('Kept from earlier conversations, one line per topic. Before work a topic touches, read it with run_tool("recall", '
                '{"topic": "<topic>"}) and follow it unless this conversation says otherwise. If a fact says to use the brand\'s own '
                "photos and none is attached, ask the marketer for the photo instead of writing a poster.")


def memory_index(rows: list[UserMemory]) -> str:
    if not rows:
        return ""
    by_topic: dict[str, list[UserMemory]] = {}
    for row in rows:
        by_topic.setdefault(topic_of(row), []).append(row)
    lines = []
    for topic, kept in by_topic.items():
        line = f'- {topic}: {len(kept)} {"fact" if len(kept) == 1 else "facts"} · recall("{topic}")'
        lines.append(line if len(line) <= LINE_CAP else line[: LINE_CAP - 1] + "…")
    return INDEX_HEADER + "\n" + "\n".join(lines)


def recall(rows: list[UserMemory], topic: str) -> str:
    found = [row for row in rows if topic_of(row) == topic.strip().lower()]
    if not found:
        return f'Nothing kept under "{topic}". Topics: ' + ", ".join(sorted({topic_of(row) for row in rows}))
    return "\n".join(f"- {row.memory} ({kind_of(row) or 'no kind'})" for row in found)
