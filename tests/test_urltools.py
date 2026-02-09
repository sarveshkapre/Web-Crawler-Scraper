from __future__ import annotations

from webcrawler.urltools import normalize_url, resolve_and_normalize


def test_normalize_url_strips_fragment_and_default_ports() -> None:
    assert normalize_url("HTTP://Example.COM:80/a#frag") == "http://example.com/a"
    assert normalize_url("https://Example.COM:443/a#frag") == "https://example.com/a"


def test_normalize_url_strips_selected_query_params_case_insensitive() -> None:
    assert (
        normalize_url(
            "https://example.com/a?utm_source=X&x=1&UTM_MEDIUM=y",
            strip_query_params={"utm_source", "utm_medium"},
        )
        == "https://example.com/a?x=1"
    )


def test_normalize_url_resolves_dot_segments_and_preserves_trailing_slash() -> None:
    assert normalize_url("https://example.com/a/./b/../c/") == "https://example.com/a/c/"
    assert normalize_url("https://example.com/a/./b/../c") == "https://example.com/a/c"


def test_resolve_and_normalize_joins_relative_links() -> None:
    assert (
        resolve_and_normalize("../x#y", base_url="https://example.com/a/b/c")
        == "https://example.com/a/x"
    )


def test_resolve_and_normalize_strips_query_params() -> None:
    assert (
        resolve_and_normalize(
            "/x?utm_source=a&k=v",
            base_url="https://example.com/a/b",
            strip_query_params={"utm_source"},
        )
        == "https://example.com/x?k=v"
    )
