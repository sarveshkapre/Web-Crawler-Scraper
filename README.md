# Web-Crawler-Scraper (`webcrawler`)

A small, production-minded web crawler and scraper CLI focused on:
- Crawl control (allowed domains, max pages, timeouts)
- Politeness (robots.txt obeyed by default, per-host delays)
- Reliability (bounded retries/backoff)
- Simple extraction (optional "secret flag" extraction)

## Requirements
- Python 3.10+

## Install (Recommended: virtualenv)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

## Usage
Crawl a site (defaults to allowed domain(s) derived from `--start-url`):
```bash
webcrawler --start-url https://example.com --max-pages 200
```

Allow multiple domains:
```bash
webcrawler --start-url https://example.com --allowed-domain example.com --allowed-domain www.example.com
```

Disable robots.txt (only for controlled environments):
```bash
webcrawler --start-url https://example.com --no-robots
```

Add a per-host delay:
```bash
webcrawler --start-url https://example.com --delay 0.25
```

## Login (Optional)
If you need a basic form-based login, provide `--login-url` and credentials. The crawler will:
1. GET the login page
2. Extract hidden `<input>` fields
3. POST hidden fields + provided credentials
4. Use the post-login URL as a start URL (if you didn't provide `--start-url`)

```bash
webcrawler \
  --login-url https://target.example/login \
  --username alice \
  --password '...redacted...' \
  --start-url https://target.example/app
```

## Secret Flag Extraction (Optional)
To extract values from `<h2 class="secret_flag">FLAG: ...</h2>`:
```bash
webcrawler --start-url https://example.com --extract-secret-flags --max-flags 5
```

Flags are printed to stdout (one per line). Logs go to stderr.

## Structured Outputs (Optional)
Write crawl fetch events as JSONL:
```bash
webcrawler --start-url https://example.com --max-pages 200 --out-urls urls.jsonl
```

Write extracted flags to a file (still prints flags to stdout for compatibility):
```bash
webcrawler --start-url https://example.com --extract-secret-flags --out-flags flags.txt
```

If output files already exist, `webcrawler` fails by default. Use `--append-output` to append.

## Persistence / Resume (Optional)
Persist crawl state (frontier + visited) to a JSON file:
```bash
webcrawler --start-url https://example.com --state crawl_state.json
```

Resume later (outputs should generally use `--append-output` when resuming):
```bash
webcrawler --state crawl_state.json --resume --append-output --out-urls urls.jsonl
```

By default, state is checkpointed every 50 fetched pages; configure via `--checkpoint-every`.

## Development
```bash
make lint
make test
make smoke
```

For running from a repo checkout without installing, `./webcrawler` works as long as your
active `python3` environment has dependencies installed (for example after activating `.venv`).
