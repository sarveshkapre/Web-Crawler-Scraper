from __future__ import annotations

import gzip
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

import lxml.etree
import requests

from .urltools import is_allowed_host, normalize_url

LOG = logging.getLogger(__name__)


_SITEMAP_MAGIC_GZIP = b"\x1f\x8b"


@dataclass(frozen=True)
class SitemapSeedSummary:
    sitemaps_fetched: int
    urls_parsed: int
    urls_kept: int
    errors: int


def extract_sitemap_urls_from_robots(body: str) -> list[str]:
    """
    Extract `Sitemap:` declarations from robots.txt content.

    This is a common discovery path for sitemap URLs.
    """
    out: list[str] = []
    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if not line.lower().startswith("sitemap:"):
            continue
        url = line.split(":", 1)[1].strip()
        if url:
            out.append(url)
    return out


def _read_limited(resp: requests.Response, *, max_bytes: int) -> bytes:
    if max_bytes <= 0:
        return resp.content
    buf = bytearray()
    for chunk in resp.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise ValueError(f"sitemap exceeded max_bytes={max_bytes}")
    return bytes(buf)


def _maybe_gunzip(raw: bytes, *, hint_url: str) -> bytes:
    # requests automatically decodes Content-Encoding: gzip, but sitemaps are often served as
    # a .gz file without a Content-Encoding header.
    if hint_url.lower().endswith(".gz") or raw.startswith(_SITEMAP_MAGIC_GZIP):
        try:
            return gzip.decompress(raw)
        except OSError:
            return raw
    return raw


def _parse_sitemap_xml(xml_bytes: bytes) -> tuple[list[str], list[str]]:
    """
    Return (urls, nested_sitemaps) from either `urlset` or `sitemapindex`.
    """
    root = lxml.etree.fromstring(xml_bytes)  # noqa: S320 (trusted input is not assumed)
    tag = lxml.etree.QName(root.tag).localname.lower()

    if tag == "urlset":
        urls: list[str] = []
        for loc in root.findall(".//{*}url/{*}loc"):
            if loc.text and loc.text.strip():
                urls.append(loc.text.strip())
        return urls, []

    if tag == "sitemapindex":
        sitemaps: list[str] = []
        for loc in root.findall(".//{*}sitemap/{*}loc"):
            if loc.text and loc.text.strip():
                sitemaps.append(loc.text.strip())
        return [], sitemaps

    return [], []


def seed_from_sitemaps(
    *,
    session: requests.Session,
    sitemap_urls: list[str],
    timeout_s: float,
    allowed_hosts: set[str] | None,
    include_patterns: tuple[re.Pattern, ...] = (),
    exclude_patterns: tuple[re.Pattern, ...] = (),
    strip_query_params: set[str] | frozenset[str] | None = None,
    max_urls: int = 20_000,
    max_sitemaps: int = 100,
    max_bytes: int = 10_000_000,
) -> tuple[list[str], SitemapSeedSummary]:
    """
    Fetch and parse sitemap URL(s), returning a unique list of normalized URLs to seed into the
    crawl.

    - Supports `urlset` and `sitemapindex` (nested).
    - Enforces allowed hosts and include/exclude patterns on the *normalized* URL.
    """
    def _url_allowed(u: str) -> bool:
        if include_patterns and not any(r.search(u) for r in include_patterns):
            return False
        if exclude_patterns and any(r.search(u) for r in exclude_patterns):
            return False
        return True

    # Normalize sitemap URLs too, so redirect/query variants don't cause repeated fetches.
    q: list[str] = [
        normalize_url(u, strip_query_params=strip_query_params)
        for u in sitemap_urls
        if str(u).strip()
    ]
    seen_sitemaps: set[str] = set()
    out: list[str] = []
    out_set: set[str] = set()
    fetched = 0
    parsed = 0
    kept = 0
    errors = 0

    while q and len(seen_sitemaps) < max_sitemaps and (max_urls <= 0 or len(out) < max_urls):
        sm_url = q.pop(0)
        if sm_url in seen_sitemaps:
            continue
        parts = urlsplit(sm_url)
        if parts.scheme not in ("http", "https"):
            continue
        seen_sitemaps.add(sm_url)

        try:
            resp = session.get(sm_url, timeout=timeout_s, allow_redirects=True, stream=True)
            if resp.status_code >= 400:
                continue
            raw = _read_limited(resp, max_bytes=max_bytes)
            body = _maybe_gunzip(raw, hint_url=sm_url)
            urls, nested = _parse_sitemap_xml(body)
            fetched += 1
        except Exception as e:
            errors += 1
            LOG.debug("sitemap fetch/parse failed url=%s err=%s", sm_url, e)
            continue

        # Queue nested sitemaps first.
        for nxt in nested:
            nu = normalize_url(nxt, strip_query_params=strip_query_params)
            if nu and nu not in seen_sitemaps:
                q.append(nu)

        for u in urls:
            parsed += 1
            nu = normalize_url(u, strip_query_params=strip_query_params)
            if not nu:
                continue
            if not is_allowed_host(nu, allowed_hosts):
                continue
            if not _url_allowed(nu):
                continue
            if nu in out_set:
                continue
            out_set.add(nu)
            out.append(nu)
            kept += 1
            if max_urls > 0 and len(out) >= max_urls:
                break

    return out, SitemapSeedSummary(
        sitemaps_fetched=fetched,
        urls_parsed=parsed,
        urls_kept=kept,
        errors=errors,
    )
