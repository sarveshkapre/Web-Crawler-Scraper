from __future__ import annotations

from webcrawler.cli import main


def _assert_usage_error(args: list[str], capsys, msg: str) -> None:
    code = main(args)
    assert code == 2
    err = capsys.readouterr().err
    assert msg in err


def test_cli_rejects_nonpositive_max_pages(capsys) -> None:
    _assert_usage_error(
        ["--start-url", "https://example.com", "--max-pages", "0"],
        capsys,
        "--max-pages",
    )


def test_cli_rejects_negative_delay(capsys) -> None:
    _assert_usage_error(["--start-url", "https://example.com", "--delay", "-1"], capsys, "--delay")


def test_cli_rejects_nonpositive_timeout(capsys) -> None:
    _assert_usage_error(
        ["--start-url", "https://example.com", "--timeout", "0"],
        capsys,
        "--timeout",
    )


def test_cli_rejects_invalid_sitemap_limits(capsys) -> None:
    _assert_usage_error(
        ["--start-url", "https://example.com", "--sitemap-max-sitemaps", "0"],
        capsys,
        "--sitemap-max-sitemaps",
    )
