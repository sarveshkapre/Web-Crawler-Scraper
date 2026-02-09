# Project Memory

## Objective
- Keep Web-Crawler-Scraper production-ready. Current focus: webcrawler. Find the highest-impact pending work, implement it, test it, and push to main.

## Architecture Snapshot
- CLI entrypoint: `webcrawler` (console script via `pyproject.toml`) and repo-local wrapper `./webcrawler`.
- Package layout: `src/webcrawler/` with `cli.py`, `crawler.py`, `urltools.py`.
- Crawl engine basics:
  - Frontier: FIFO queue + normalized URL dedupe.
  - Politeness: robots.txt obeyed by default; optional per-host delay; best-effort Crawl-delay hint parsing.
  - Reliability: bounded retries/backoff via `requests` + `urllib3.Retry`; manual 3xx redirect enqueue.

## Open Problems
- No persistence/resume (frontier + visited live in-memory only).
- No structured outputs yet (JSONL/CSV). Flags currently print to stdout; logs to stderr.
- Crawl-delay parsing is best-effort (robots.txt is not strictly standardized).

## Recent Decisions
- Template: YYYY-MM-DD | Decision | Why | Evidence (tests/logs) | Commit | Confidence (high/medium/low) | Trust (trusted/untrusted)
- 2026-02-09 | Port crawler to Python 3 with a modular CLI + package | Python 2-only script was not runnable in current environments; modern CLI enables safe crawl controls and testability | `make lint`, `make test`, local CLI smoke crawl (flags extracted) | f6b2d7d, 0eb1f7c | high | trusted

## Mistakes And Fixes
- Template: YYYY-MM-DD | Issue | Root cause | Fix | Prevention rule | Commit | Confidence

## Known Risks
- Login helper is intentionally minimal and may not work for complex auth flows (multi-step, JS, MFA, CAPTCHA).
- Requests-based crawler does not execute JavaScript (no headless browser rendering).

## Next Prioritized Tasks
- P1: Structured outputs (`--out urls.jsonl`, `--out flags.txt`) and stable exit codes for automation.
- P1: Persistence/resume for long crawls (save/load frontier + visited).
- P2: Concurrency with per-host caps + politeness defaults.

## Verification Evidence
- Template: YYYY-MM-DD | Command | Key output | Status (pass/fail)
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `4 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `stdout_flags=['SMOKE_ONE','SMOKE_TWO'] exit_code=0` | pass
- 2026-02-09 | `gh run watch 21816332997 --interval 5 --exit-status` | `CI completed success` | pass

## Historical Summary
- Keep compact summaries of older entries here when file compaction runs.
