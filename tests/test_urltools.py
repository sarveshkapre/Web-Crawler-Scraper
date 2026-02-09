from __future__ import annotations

from webcrawler.urltools import normalize_url, resolve_and_normalize


def test_normalize_url_strips_fragment_and_default_ports() -> None:
    assert normalize_url("HTTP://Example.COM:80/a#frag") == "http://example.com/a"
    assert normalize_url("https://Example.COM:443/a#frag") == "https://example.com/a"


def test_normalize_url_resolves_dot_segments_and_preserves_trailing_slash() -> None:
    assert normalize_url("https://example.com/a/./b/../c/") == "https://example.com/a/c/"
    assert normalize_url("https://example.com/a/./b/../c") == "https://example.com/a/c"


def test_resolve_and_normalize_joins_relative_links() -> None:
    assert (
        resolve_and_normalize("../x#y", base_url="https://example.com/a/b/c")
        == "https://example.com/a/x"
    )

