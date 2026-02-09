from __future__ import annotations

import posixpath
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


def normalize_url(
    url: str,
    *,
    drop_fragment: bool = True,
    strip_query_params: set[str] | frozenset[str] | None = None,
) -> str:
    """
    Normalize enough for crawl dedupe:
    - lower-case scheme/host
    - strip fragments
    - remove default ports
    - resolve dot segments in path
    - optionally strip selected query parameters (case-insensitive match on parameter name)
    """
    parts = urlsplit(url)
    scheme = (parts.scheme or "http").lower()
    netloc = parts.netloc.lower()

    host, sep, port = netloc.partition(":")
    if sep:
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host

    path = parts.path or "/"
    keep_trailing = path.endswith("/") and path != "/"
    path = posixpath.normpath(path)
    if keep_trailing and not path.endswith("/"):
        path += "/"
    if not path.startswith("/"):
        path = "/" + path

    query = parts.query
    if strip_query_params:
        strip = {p.lower() for p in strip_query_params if p}
        if strip and query:
            kept = [
                (k, v)
                for (k, v) in parse_qsl(query, keep_blank_values=True)
                if k.lower() not in strip
            ]
            query = urlencode(kept, doseq=True)

    fragment = "" if drop_fragment else parts.fragment
    return urlunsplit((scheme, netloc, path, query, fragment))


def resolve_and_normalize(
    href: str,
    *,
    base_url: str,
    strip_query_params: set[str] | frozenset[str] | None = None,
) -> str | None:
    href = (href or "").strip()
    if not href:
        return None
    if href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    return normalize_url(urljoin(base_url, href), strip_query_params=strip_query_params)


def host_for_url(url: str) -> str:
    return urlsplit(url).netloc.split("@")[-1].split(":")[0].lower()


def is_allowed_host(url: str, allowed_hosts: set[str] | None) -> bool:
    if not allowed_hosts:
        return True
    return host_for_url(url) in allowed_hosts
