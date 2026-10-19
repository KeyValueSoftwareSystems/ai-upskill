import hashlib
import threading
from functools import lru_cache
from pathlib import Path

import lancedb
import pyarrow as pa

from launchkit.harness.request import WORKSPACE_ID, UnknownWorkspace
from launchkit.harness.search import TOP_K, Chunk, chunk_text, embed, load_chunks

TABLE = "chunks"
DIMENSIONS = 384
SCHEMA = pa.schema(
    [
        pa.field("ref", pa.string()),
        pa.field("workspace", pa.string()),
        pa.field("heading", pa.string()),
        pa.field("text", pa.string()),
        pa.field("hash", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), DIMENSIONS)),
    ]
)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def scope(workspace_id: str) -> str:
    """A filter on the workspace column. The id is checked against the allow-list because it is written into the query."""
    if not WORKSPACE_ID.match(workspace_id):
        raise UnknownWorkspace(workspace_id)
    return f"workspace = '{workspace_id}'"


class BrandStore:
    """A vector database: every brand's chunks in one LanceDB table on disk, one row per chunk with its vector.
    Written when a brand document is processed (onboarding, upload, `launchkit index`), read on every lookup.
    The vectors survive a restart. A chunk is embedded again only when its text changes."""

    def __init__(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(path))
        self.lock = threading.Lock()
        self.table = self.db.create_table(TABLE, schema=SCHEMA, exist_ok=True)

    def rows(self, workspace_id: str) -> list[dict]:
        return self.table.search().where(scope(workspace_id)).select(["ref", "hash", "vector"]).limit(None).to_list()

    def indexed(self, workspace_id: str) -> int:
        """How many chunks this workspace has in the store. 0 means its documents were never processed."""
        return self.table.count_rows(scope(workspace_id))

    def index(self, workspace_id: str, root: Path) -> int:
        """Document processing: chunk one workspace's brand files, embed what is new or changed, and replace
        that workspace's rows. Returns how many chunks had to be embedded."""
        with self.lock:
            chunks = load_chunks(root)
            wanted = [(c, text_hash(chunk_text(c))) for c in chunks]
            stored = self.rows(workspace_id)
            if sorted((r["ref"], r["hash"]) for r in stored) == sorted((c.ref, h) for c, h in wanted):
                return 0
            known = {r["hash"]: r["vector"] for r in stored}
            missing = [(c, h) for c, h in wanted if h not in known]
            fresh = dict(zip((h for _, h in missing), embed([chunk_text(c) for c, _ in missing]))) if missing else {}
            self.table.delete(scope(workspace_id))
            if wanted:
                self.table.add(
                    [
                        {"ref": c.ref, "workspace": workspace_id, "heading": c.heading, "text": c.text, "hash": h, "vector": known.get(h) or fresh[h]}
                        for c, h in wanted
                    ]
                )
            return len(missing)

    def search(self, query: str, k: int = TOP_K) -> list[tuple[float, Chunk]]:
        """Semantic search: embed the question, rank every row by cosine similarity to it, keep the top k.
        Every row in the table takes part, whichever brand it belongs to."""
        rows = self.table.search(embed([query])[0]).metric("cosine").limit(k).to_list()
        return [
            (1 - r["_distance"], Chunk(id=r["ref"].split("/", 1)[1], heading=r["heading"], text=r["text"], workspace=r["workspace"]))
            for r in rows
        ]


@lru_cache(maxsize=None)
def brand_store(path: Path) -> BrandStore:
    return BrandStore(path)


def index_brand(workspace_id: str, settings, trace=None) -> tuple[int, int]:
    """Index one brand's documents into the store. Returns (chunks stored, chunks embedded this time)."""
    if not WORKSPACE_ID.match(workspace_id) or not (settings.workspaces_dir / workspace_id).is_dir():
        raise UnknownWorkspace(workspace_id)
    store = brand_store(settings.data_dir / "brand-store")
    embedded = store.index(workspace_id, settings.workspaces_dir / workspace_id)
    stored = store.indexed(workspace_id)
    if trace is not None:
        trace.note(f"indexed {workspace_id}: {stored} chunks in the brand store, {embedded} embedded now, the rest unchanged")
    return stored, embedded
