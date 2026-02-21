# Repo cleanup for public release — Verification spike

## What README currently contains (user vs dev/internal)

- **User-facing**: Title, short description ("OHLCV data fetching and processing tool"), Installation (only dev install shown), Usage (doctor, fetch 1d/1w, --feed), Fetch Command Output (what 1d does, output file names, validation_report), Configuration (env vars), License.
- **Dev/internal**: Development section with pytest, bandit, pip-audit; **publishing instructions** (PyPI, tag, link to docs/changes/2026-02-20-security-ci-publish.md) — to be removed from README and kept only in internal docs.
- **Gaps for end users**: No "pip install ohlcv-hub" for users (post-publish); no explicit "Features" list; no minimal schema table; no "Notes / Limitations (MVP)" (intraday, realtime, Alpaca feed caveats).

## docs/changes and docs/llm-handoff — stay vs move

- **docs/changes/** (8 files): All are internal changelog/implementation notes. **Move** to docs/internal/changes/.
- **docs/llm-handoff/** (10 files): All are internal planning/handoff. **Move** to docs/internal/llm-handoff/.
- **docs/process.md**: Internal process log. **Move** to docs/internal/process.md.
- No docs file needs to stay at top-level docs/ for end users; move all of the above under docs/internal/.

## Current .gitignore gaps

- Already present: .venv/, venv/, env/, __pycache__/, *.pyc (via *.py[cod]), .pytest_cache/, dist/, build/, *.egg-info/, .env, .env.local, data/, *.parquet, *.csv, .DS_Store.
- **Add**: .mypy_cache/, .ruff_cache/ (common Python tooling). Optional: validation_report.json (if we want to ignore it at repo root; data/ already covers outputs under data/). Add validation_report.json for clarity.

## Proposed final README outline

1. **Title** + one-paragraph description (dataset builder, US stocks/ETFs, 1d fetched / 1w resampled, Alpaca, Parquet/CSV, validation report).
2. **Features** — short bullets (daily bars, weekly resampled, validation + missing days, Parquet/CSV, rate-limit handling, etc.).
3. **Quickstart** — pip install (users: `pip install ohlcv-hub` once published), dev install `pip install -e ".[dev]"`, env vars (ALPACA_API_KEY, ALPACA_API_SECRET, optional BASE_URL), example commands (1d, 1w, --feed).
4. **Output** — output file names for 1d/1w, validation_report.json; **schema table**: symbol, timeframe, ts, open, high, low, close, volume, source, currency, adjustment.
5. **Notes / Limitations (MVP)** — no intraday, no realtime, no strategies; Alpaca subscription/feed (iex vs sip).
6. **Development** — minimal: tests (pytest), lint/security (bandit, pip-audit). No publishing steps.
7. **License** — MIT.
