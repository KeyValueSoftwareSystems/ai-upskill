from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def out_dir(conversation_id: str) -> Path:
    path = OUT / conversation_id
    path.mkdir(parents=True, exist_ok=True)
    return path
