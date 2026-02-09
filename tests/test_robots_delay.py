from __future__ import annotations

from webcrawler.crawler import _parse_crawl_delay


def test_parse_crawl_delay_multiple_user_agent_lines_same_group() -> None:
    body = "User-agent: Bingbot\nUser-agent: Googlebot\nCrawl-delay: 7\n"
    assert _parse_crawl_delay(body, user_agent="Bingbot") == 7.0


def test_parse_crawl_delay_exact_user_agent_overrides_star() -> None:
    body = (
        "User-agent: *\n"
        "Crawl-delay: 10\n"
        "User-agent: webcrawler-scraper/0.1\n"
        "Crawl-delay: 1\n"
    )
    assert _parse_crawl_delay(body, user_agent="webcrawler-scraper/0.1") == 1.0


def test_parse_crawl_delay_starts_new_group_after_directives() -> None:
    body = "User-agent: *\nDisallow: /\nUser-agent: xbot\nCrawl-delay: 2\n"
    assert _parse_crawl_delay(body, user_agent="xbot") == 2.0

