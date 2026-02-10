# Project Memory

## Objective
- Keep Web-Crawler-Scraper production-ready. Current focus: webcrawler. Find the highest-impact pending work, implement it, test it, and push to main.

## Architecture Snapshot
- CLI entrypoint: `webcrawler` (console script via `pyproject.toml`) and repo-local wrapper `./webcrawler`.
- Package layout: `src/webcrawler/` with `cli.py`, `crawler.py`, `sitemaps.py`, `state.py`, `urltools.py`.
- Crawl engine basics:
  - Frontier: FIFO queue + normalized URL dedupe.
  - Politeness: robots.txt obeyed by default; optional per-host delay; Crawl-delay hint parsing (best-effort).
  - Reliability: bounded retries/backoff via `requests` + `urllib3.Retry`; manual 3xx redirect enqueue.
  - Outputs: optional JSONL fetch event stream (`--out-urls`) and line-based flags output (`--out-flags`).
  - Persistence: optional `--state` checkpointing + `--resume`.

## Open Problems
- No concurrency (single-threaded fetch loop).

## Recent Decisions
- Template: YYYY-MM-DD | Decision | Why | Evidence (tests/logs) | Commit | Confidence (high/medium/low) | Trust (trusted/untrusted)
- 2026-02-10 | Add `--max-depth` hop limit + persist hop depths in state v2 | Depth limits are a core crawl control to bound traversal; persisting depth preserves semantics across resume/checkpoint runs | `make lint`, `make test`, `make smoke`, new max-depth + sitemap depth tests, GitHub Actions CI success | 6600ade | high | trusted
- 2026-02-10 | Add `--robots-fail-closed` hard politeness mode | Some controlled environments prefer failing closed when robots.txt is unavailable, preventing accidental non-compliance | `make lint`, `make test`, new robots fail-closed test, GitHub Actions CI success | 6600ade | high | trusted
- 2026-02-09 | Add sitemap seeding (`--sitemap-url`, `--sitemap-auto`, `--sitemap-from-robots`) | Helps find pages that are not discoverable via link traversal; keeps crawler useful on sites with sparse navigation | `make lint`, `make test`, `make smoke`, new sitemap seeding tests, GitHub Actions CI success | 7e96dc2 | high | trusted
- 2026-02-09 | Add optional tracking-param stripping (`--strip-query-param`, `--strip-utm`) applied before dedupe | Reduces duplicated crawl work caused by analytics query params; improves crawl coverage under a fixed max-pages budget | `make lint`, `make test`, `make smoke`, new CLI + urltools tests, GitHub Actions CI success | 603971c | high | trusted
- 2026-02-09 | Port crawler to Python 3 with a modular CLI + package | Python 2-only script was not runnable in current environments; modern CLI enables safe crawl controls and testability | `make lint`, `make test`, local CLI smoke crawl (flags extracted) | f6b2d7d, 0eb1f7c | high | trusted
- 2026-02-09 | Add structured outputs + persistence/resume + improved Crawl-delay parsing | Automation needs file outputs; long crawls need checkpoint/resume; Crawl-delay parsing needed basic correctness for multi-User-agent groups | `make lint`, `make test`, `make smoke`, new tests for CLI outputs/resume and Crawl-delay parsing | eef8325, 2c76e2f | high | trusted
- 2026-02-09 | Add machine-readable crawl summary (`--summary-json`) + document stable exit codes | Makes CLI automation-friendly without breaking flag-extraction stdout contract | `make lint`, `make test`, `make smoke`, new tests for summary output | 4cd0f87 | high | trusted
- 2026-02-09 | Add URL allow/deny regex filters (`--include-regex`, `--exclude-regex`) | Common crawler control needed to target sections and avoid irrelevant pages | `make lint`, `make test`, new tests for include/exclude behavior | f864a1f | high | trusted

## Mistakes And Fixes
- Template: YYYY-MM-DD | Issue | Root cause | Fix | Prevention rule | Commit | Confidence

## Known Risks
- Login helper is intentionally minimal and may not work for complex auth flows (multi-step, JS, MFA, CAPTCHA).
- Requests-based crawler does not execute JavaScript (no headless browser rendering).

## Next Prioritized Tasks
- P2: Concurrency with per-host caps + politeness defaults.
- P3: Retry-on-exception with cap.
- P3: Response size cap (`--max-body-bytes`).

## Verification Evidence
- Template: YYYY-MM-DD | Command | Key output | Status (pass/fail)
- 2026-02-10 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-10 | `. .venv/bin/activate && make test` | `22 passed` | pass
- 2026-02-10 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-10 | `gh run watch 21847423285 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-10 | `gh run watch 21847476705 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `4 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `stdout_flags=['SMOKE_ONE','SMOKE_TWO'] exit_code=0` | pass
- 2026-02-09 | `gh run watch 21816332997 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `9 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `stdout_flags=['SMOKE_ONE','SMOKE_TWO'] exit_code=0` | pass
- 2026-02-09 | `gh run watch 21824043405 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `gh run watch 21831982485 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `11 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21832003543 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `13 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21832092071 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `gh run watch 21832159506 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `16 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21841017448 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `19 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21841156652 --interval 5 --exit-status` | `CI completed success` | pass

## Historical Summary
- Keep compact summaries of older entries here when file compaction runs.
