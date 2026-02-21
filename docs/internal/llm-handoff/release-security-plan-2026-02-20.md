# Release & Security CI — Verification spike

## Current packaging metadata

- **name**: ohlcv-hub  
- **version**: 0.1.0  
- **readme**: README.md  
- **license**: MIT (text)  
- **requires-python**: >=3.9  
- **classifiers**: Development Status Alpha, License OSI MIT, Python 3.9–3.12  
- **entrypoints**: `[project.scripts]` → `ohlcv-hub = ohlcv_hub.cli:app` (Typer app, not a callable; may need `app` as callable for CLI — current setup uses Typer’s app)  
- **dependencies**: httpx, pandas, pyarrow, typer, python-dateutil, pandas_market_calendars  
- **optional-dependencies**: dev = pytest only (no bandit/pip-audit yet)  
- **build**: setuptools.build_meta; packages = ["ohlcv_hub", "ohlcv_hub.providers"] (explicit list; consider setuptools find for subpackages)

## Current test command(s)

- `pytest` (testpaths = ["tests"]; no coverage or extra args in pyproject)  
- README: `pytest`, `pytest -v`  
- Local: `pytest -q` for quick run

## Current docs/changes state

- docs/changes/: 2026-02-20-*.md (bootstrap, alpaca-client-contract, fetch-1d, fetch-1w, feed-option, retry-429, proactive-rate-limit, debug-logging). Append-only changelog pattern.

## Security-sensitive behaviors

- **Env**: config.py uses `os.getenv("ALPACA_API_KEY", "")`, `ALPACA_API_SECRET`, `ALPACA_DATA_BASE_URL`. No secrets in code.  
- **CLI doctor**: Prints masked keys only (`'*' * min(len(key), 8)...`).  
- **AlpacaClient**: Receives api_key/api_secret in __init__, uses only in _build_auth_headers() for request headers; no logging of secrets.  
- **Logging**: alpaca.py logs only rate-limit/retry metadata (remaining, reset, sleep_secs, strategy); no headers or request bodies.  
- **.env**: Should remain in .gitignore (not verified here; assume present).

## Proposed CI matrix and publish approach

- **CI matrix**: python-version: ["3.9", "3.10", "3.11", "3.12"] to match classifiers.  
- **Publish**: Prefer **PyPI Trusted Publishing** (OIDC, no long-lived token): workflow gets `id-token: write`, use `pypa/gh-action-pypi-publish@release/v1` with no PYPI_API_TOKEN.  
- **Alternative**: If Trusted Publishing not set up yet, document API token in secret PYPI_API_TOKEN; prefer Trusted Publishing in docs.
