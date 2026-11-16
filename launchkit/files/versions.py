"""Stretch, after stage 4: what an edit needs to know to refuse a stale write.

read_file remembers a fingerprint of each file it reads. edit_file takes a lock on the file, compares the file's
fingerprint now with the one remembered, and writes only if they match. The comparison and the write happen under
the same lock, so no other writer can slip in between them: a check followed by a separate write has the same gap.

The lock covers writers in this process. Two processes need a file lock, and a bucket needs a conditional write.

Reference page 8, What an edit tool can and cannot check.
"""

import hashlib
import threading
from pathlib import Path

_LOCKS: dict[str, threading.Lock] = {}
_GUARD = threading.Lock()


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lock_for(path: Path) -> threading.Lock:
    """One lock per file, made on first use."""
    with _GUARD:
        return _LOCKS.setdefault(str(path), threading.Lock())
