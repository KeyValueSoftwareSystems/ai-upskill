"""Past turns of one conversation, kept in a SQLite file so the agent remembers them."""

from agno.db.sqlite import SqliteDb


def session_db(settings) -> SqliteDb:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file=str(settings.data_dir / "sessions.db"))
