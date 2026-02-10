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
    ver = int(data.get("version") or 0)
    if ver not in {1, 2}:
        raise ValueError("unsupported state version")

    raw_start = data.get("start_urls") or []
    start_urls = tuple(normalize_url(u) for u in raw_start)

    raw_allowed = data.get("allowed_hosts")
    allowed_hosts = None
    if raw_allowed is not None:
        allowed_hosts = {str(x).lower() for x in raw_allowed if str(x).strip()}

    frontier_items: list[tuple[str, int]] = []
    raw_frontier = data.get("frontier") or []
    if ver == 1:
        for u in raw_frontier:
            frontier_items.append((normalize_url(str(u)), 0))
    else:
        for item in raw_frontier:
            if isinstance(item, str):
                frontier_items.append((normalize_url(item), 0))
                continue
            if isinstance(item, dict):
                u = normalize_url(str(item.get("url") or ""))
                if not u:
                    continue
                try:
                    d = int(item.get("depth") or 0)
                except Exception:
                    d = 0
                if d < 0:
                    d = 0
                frontier_items.append((u, d))
                continue
            if isinstance(item, (list, tuple)) and len(item) == 2:
                u = normalize_url(str(item[0] or ""))
                if not u:
                    continue
                try:
                    d = int(item[1] or 0)
                except Exception:
                    d = 0
                if d < 0:
                    d = 0
                frontier_items.append((u, d))
    seen = {normalize_url(u) for u in (data.get("seen") or [])}
    flags = {str(x) for x in (data.get("flags") or []) if str(x)}
    pages_fetched = int(data.get("pages_fetched") or 0)

    st = CrawlState(
        frontier=deque(frontier_items),
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
        "version": 2,
        "start_urls": list(start_urls),
        "allowed_hosts": sorted(allowed_hosts) if allowed_hosts is not None else None,
        "pages_fetched": state.pages_fetched,
        "frontier": [{"url": u, "depth": int(d)} for (u, d) in state.frontier],
        "seen": list(state.seen),
        "flags": sorted(state.flags),
    }
    tmp.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, p)
