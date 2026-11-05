"""What the agent keeps across conversations: Agno's memory table, in the same SQLite file as the chat history.

One Db object holds both, each in its own table: the session rows (one conversation, while it lasts) and the memory
rows (what outlives it). LaunchKit writes its own system message (Session 1's ContextBuilder), so Agno's
add_memories_to_context never reaches the prompt here. memory_text does what Agno's default does instead: every row
this person may read, in the prompt, every turn.
"""

from pathlib import Path

import yaml
from agno.db.schemas.memory import UserMemory
from agno.db.sqlite import SqliteDb

from launchkit.memory.write_gate import ask_before_keeping
from launchkit.tools.catalogue import built
from launchkit.trace import Trace

MEMORY_TABLE = "agno_memories"
KINDS = ("preference", "domain fact", "workflow", "correction")
OWNED = ("author:", "source:")
SAMPLES = Path(__file__).resolve().parents[2] / "samples" / "memory"
RULES = Path(__file__).resolve().parent / "write_rules.md"

# Agno's own instruction for update_user_memory (agno/agent/_messages.py, <updating_user_memories>) never reaches
# LaunchKit's system message, so the harness says it, worded for the three doors. MEMORY_TASK opens the Task section:
# placed anywhere later, "call find_tool first" wins and the model rarely calls the memory tool at all.
MEMORY_TASK = ('Before find_tool: if the message states a rule, preference or correction meant to last ("use our...", '
               '"never...", "always...", "from now on..."), call update_user_memory first, directly, with it in one sentence. '
               "When unsure, call it. Then call find_tool for the job as usual.")
MEMORY_SHARE = ("Call update_user_memory as well when the marketer wants something already kept changed, or kept for "
                "everyone at the brand: who it is for is new, even when the fact is not.")

MEMORY_HEADER = ("Kept from earlier conversations. Follow these unless this conversation says otherwise. If one says to use "
                 "the brand's own photos and none is in this conversation, ask the marketer for the photo instead of writing a poster.")


def everyone(workspace_id: str) -> str:
    """The id a row kept for everyone in a workspace is filed under. Agno scopes memory by user id only, so the
    workspace tier is a user id of its own."""
    return f"{workspace_id}:everyone"


class MemoryDb(SqliteDb):
    """The agent's database: Agno's SqliteDb with a door on one write. Sessions and runs pass through unchanged; every
    memory row goes through upsert_user_memory first and gets the fields the harness owns, never the agent: who said
    it and where it came from. Once ask_before_keeping is built, Maya says yes or no to each row first, and whether it
    is hers or everyone's at the workspace. The door sits inside the database because Agno's memory manager writes
    straight to whatever db it is given."""

    def __init__(self, db_file: str, workspace_id: str, user_id: str, trace: Trace | None = None, approve=None, name: str | None = None):
        super().__init__(db_file=db_file, memory_table=MEMORY_TABLE)
        self.workspace_id, self.user_id = workspace_id, user_id
        self.name = name or user_id.capitalize()
        self.trace = trace if trace is not None else Trace()
        self.approve = approve
        self.kept: list[str] = []
        self.refused: list[str] = []

    def upsert_user_memory(self, memory: UserMemory, deserialize: bool | None = True):
        scope = "user"
        if self.approve is not None and built(ask_before_keeping):
            scope = ask_before_keeping(memory.memory, list(memory.topics or []), self.approve)
            if scope is None:
                self.trace.refused("keep a memory", f"{self.name} said no to: {memory.memory}")
                self.refused.append(memory.memory)
                return None
        memory.topics = [t for t in (memory.topics or []) if not t.startswith(OWNED)] + [f"author:{self.user_id}", "source:conversation"]
        if scope == "workspace" and memory.user_id != everyone(self.workspace_id):
            # Agno's upsert never changes a row's user_id, so a row someone shares is moved: their copy goes, and
            # everyone's copy is written new.
            self.delete_user_memory(memory.memory_id)
            memory.memory_id, memory.user_id = None, everyone(self.workspace_id)
        self.trace.note(f"memory kept · {'everyone at ' + self.workspace_id if scope == 'workspace' else memory.user_id} · {memory.memory}")
        self.kept.append(memory.memory)
        return super().upsert_user_memory(memory, deserialize)


def what_was_kept(db: MemoryDb):
    """A tool hook for update_user_memory. Agno's memory manager hears "Memory added" from the database whatever the
    door decided, so its answer to the agent says a row was kept even when the marketer said no. When the door refused
    a row during the call, the agent gets what really happened instead."""

    def hook(function_name: str, function_call, arguments: dict):
        kept, refused = len(db.kept), len(db.refused)
        result = function_call(**arguments)
        if function_name != "update_user_memory" or len(db.refused) == refused:
            return result
        lines = [f"Kept: {memory}" for memory in db.kept[kept:]]
        lines += [f"Not kept, {db.name} said no: {memory}" for memory in db.refused[refused:]]
        return "\n".join(lines + ["Do not say a row was kept unless it is listed as kept here."])

    return hook


def write_rules() -> str | None:
    """The room's rules for what earns a write (memory hands-on 1, part 2), for MemoryManager(memory_capture_instructions=...).
    None until write_rules.md exists, and then Agno uses its own."""
    return RULES.read_text(encoding="utf-8") if RULES.exists() else None


def memory_db(settings, workspace_id: str, user_id: str, trace: Trace | None = None, approve=None) -> MemoryDb:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    from launchkit.brands.users import list_logins

    name = next((login["name"] for login in list_logins(settings) if login["workspace_id"] == workspace_id and login["user_id"] == user_id), None)
    return MemoryDb(str(settings.data_dir / "sessions.db"), workspace_id, user_id, trace, approve, name)


def memories_for(db: SqliteDb, workspace_id: str, user_id: str) -> list[UserMemory]:
    """Every row this person may read: their own, and the workspace's. Nobody else's."""
    rows = []
    for owner in (user_id, everyone(workspace_id)):
        rows += db.get_user_memories(user_id=owner) or []
    return rows


def kind_of(row: UserMemory) -> str:
    return next((t for t in row.topics or [] if t in KINDS), "")


def topic_of(row: UserMemory) -> str:
    """The row's subject: its first topic that is not a kind or a field the harness owns."""
    return next((t for t in row.topics or [] if t not in KINDS and not t.startswith(OWNED)), "other")


def memory_text(rows: list[UserMemory]) -> str:
    """Agno's default read path, done by hand: every row, every turn, whether or not it matters to this message."""
    if not rows:
        return ""
    return MEMORY_HEADER + "\n" + "\n".join(f"- {row.memory}" for row in rows)


def seed(settings, workspace_id: str, path: Path | None = None) -> int:
    """Write a month of rows straight into the table, as if earlier conversations had kept them. No asks: this is the
    store as it would be, not a conversation."""
    rows = yaml.safe_load((path or SAMPLES / f"{workspace_id}_month.yaml").read_text(encoding="utf-8"))
    db = SqliteDb(db_file=str(settings.data_dir / "sessions.db"), memory_table=MEMORY_TABLE)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(rows):
        owner = everyone(workspace_id) if row.get("scope") == "workspace" else row["author"]
        topics = [row["kind"], row["topic"], f"author:{row['author']}", f"source:{row.get('source', 'conversation')}"]
        db.upsert_user_memory(UserMemory(memory_id=f"seed-{workspace_id}-{i:02d}", memory=row["text"], topics=topics, user_id=owner))
    return len(rows)
