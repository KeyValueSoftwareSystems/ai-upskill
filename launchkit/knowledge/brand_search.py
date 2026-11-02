import math
import os
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

TOP_K = 5
EMBED_MODEL = os.environ.get("LAUNCHKIT_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
SOURCES = ("brand-book.md", "facts.md")
STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i if in is it its me my of on or our so that the "
    "their them they this to was we what when where which will with you your".split()
)


@dataclass(frozen=True)
class Chunk:
    id: str
    heading: str
    text: str
    workspace: str = ""

    @property
    def ref(self) -> str:
        return f"{self.workspace}/{self.id}" if self.workspace else self.id

    def render(self) -> str:
        return f"[{self.ref}] {self.heading}\n{self.text}"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def split_by_heading(text: str, source: str) -> list[Chunk]:
    """One chunk per "## " section, so each chunk is one rule or one topic and makes sense alone.
    A file with no sections (facts.md) is one fact per line."""
    if "\n## " not in "\n" + text:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return [Chunk(f"{source}#{n}", "Fact", line) for n, line in enumerate(lines, 1)]
    chunks, heading, body = [], "Introduction", []

    def flush():
        if "".join(body).strip():
            chunks.append(Chunk(f"{source}#{slug(heading)}", heading, "\n".join(body).strip()))

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            heading, body = line[3:].strip(), []
        elif not line.startswith("# "):
            body.append(line)
    flush()
    return chunks


def load_chunks(root: Path) -> list[Chunk]:
    chunks = []
    for name in SOURCES:
        path = root / name
        if path.is_file():
            chunks += [replace(c, workspace=root.name) for c in split_by_heading(path.read_text(encoding="utf-8"), name)]
    return chunks


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]


def bm25(query: str, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> list[tuple[float, Chunk]]:
    """Score each chunk by the words it shares with the query. Rare words count more; long chunks a bit less."""
    docs = [words(f"{c.heading} {c.text}") for c in chunks]
    if not docs:
        return []
    average = sum(map(len, docs)) / len(docs)
    seen_in = {}
    for doc in docs:
        for w in set(doc):
            seen_in[w] = seen_in.get(w, 0) + 1
    scored = []
    for chunk, doc in zip(chunks, docs):
        score = 0.0
        for w in set(words(query)):
            count = doc.count(w)
            if count:
                idf = math.log(1 + (len(docs) - seen_in[w] + 0.5) / (seen_in[w] + 0.5))
                score += idf * count * (k1 + 1) / (count + k1 * (1 - b + b * len(doc) / average))
        scored.append((score, chunk))
    return sorted((pair for pair in scored if pair[0] > 0), key=lambda pair: pair[0], reverse=True)


def render_results(query: str, chunks: list[Chunk]) -> str:
    if not chunks:
        return f'Nothing in the brand guide matches "{query}". Do not claim anything about it.'
    return f"{len(chunks)} sections of the brand guide that match, best first:\n\n" + "\n\n".join(c.render() for c in chunks)


@lru_cache(maxsize=1)
def embedder():
    """A small local embedding model: runs on the CPU, needs no key, and gives the same numbers on every run.
    The first call downloads it (about 130 MB) into the Hugging Face cache."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL, device="cpu")


def embed(texts: list[str]) -> list[list[float]]:
    """Text in, a list of 384 numbers per text out. Normalised, so the dot product is the cosine similarity."""
    return embedder().encode(list(texts), normalize_embeddings=True).tolist()


def chunk_text(chunk: Chunk) -> str:
    return f"{chunk.heading}\n{chunk.text}"


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))

