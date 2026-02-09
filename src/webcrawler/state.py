from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from .crawler import CrawlState
from .urltools import normalize_url


@dataclass(frozen=True)
class PersistedState:
    state: CrawlState
    start_urls: tuple[str, ...]
    allowed_hosts: set[str] | None


def load_state(path: str | Path) -> PersistedState:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("state must be a JSON object")
    if data.get("version") != 1:
        raise ValueError("unsupported state version")

    raw_start = data.get("start_urls") or []
    start_urls = tuple(normalize_url(u) for u in raw_start)

    raw_allowed = data.get("allowed_hosts")
    allowed_hosts = None
    if raw_allowed is not None:
        allowed_hosts = {str(x).lower() for x in raw_allowed if str(x).strip()}

    frontier = [normalize_url(u) for u in (data.get("frontier") or [])]
    seen = {normalize_url(u) for u in (data.get("seen") or [])}
    flags = {str(x) for x in (data.get("flags") or []) if str(x)}
    pages_fetched = int(data.get("pages_fetched") or 0)

    st = CrawlState(
        frontier=deque(frontier),
        seen=seen,
        flags=flags,
        pages_fetched=pages_fetched,
    )
    return PersistedState(state=st, start_urls=start_urls, allowed_hosts=allowed_hosts)


def save_state(
    path: str | Path,
    *,
    state: CrawlState,
    start_urls: tuple[str, ...],
    allowed_hosts: set[str] | None,
) -> None:
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    payload = {
        "version": 1,
        "start_urls": list(start_urls),
        "allowed_hosts": sorted(allowed_hosts) if allowed_hosts is not None else None,
        "pages_fetched": state.pages_fetched,
        "frontier": list(state.frontier),
        "seen": list(state.seen),
        "flags": sorted(state.flags),
    }
    tmp.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, p)
