# 2026-02-20: Security audit baseline, CI, and PyPI publish

## What changed

- **Dev dependencies**: `bandit` and `pip-audit` added to `[dev]` in `pyproject.toml` for local and CI security checks.
- **Packaging**: Setuptools now uses `packages.find` so `ohlcv_hub` and all subpackages are included in the build.
- **SECURITY.md**: Added with vulnerability reporting instructions and a note to never share API secrets in issues or logs.
- **GitHub Actions**:
  - **CI** (`.github/workflows/ci.yml`): On push/PR to `main`, runs tests, bandit, and pip-audit; matrix Python 3.9–3.12.
  - **Publish** (`.github/workflows/publish.yml`): On push of tags `v*`, builds sdist and wheel and publishes to PyPI using Trusted Publishing (no secrets in repo).

## Files touched

- `pyproject.toml` — dev extras (bandit, pip-audit), `[tool.setuptools.packages.find]`.
- `SECURITY.md` — new.
- `.github/workflows/ci.yml` — new.
- `.github/workflows/publish.yml` — new.
- `ohlcv_hub/providers/alpaca.py` — added `# nosec B105` for bandit false positive on pagination empty-string check.
- `README.md` — Development section: bandit/pip-audit commands and release pointer.
- `docs/process.md` — appended entry for this work.
- `docs/changes/2026-02-20-security-ci-publish.md` — this file.

## How to run security checks locally

- Install dev deps: `pip install -e ".[dev]"`
- Run tests: `pytest -q`
- Run bandit (static security lint on source): `bandit -r ohlcv_hub -x tests -q`
- Run pip-audit (dependency vulnerabilities; may use network): `pip-audit`  
  - Zero findings: exit 0. One or more: exit non-zero; fix by upgrading or replacing affected dependencies.

## How to release

1. Bump version in `pyproject.toml` (e.g. `0.1.0` → `0.2.0`).
2. Update changelog (e.g. add a `docs/internal/changes/YYYY-MM-DD-release.md` or update README if needed).
3. Commit, then create and push an annotated tag:  
   `git tag -a v0.2.0 -m "Release 0.2.0"` then `git push origin v0.2.0`.
4. **PyPI Trusted Publishing**: On PyPI, open the project → Publishing → Configure Trusted Publishers. Add a new publisher:
   - Owner/repo: your GitHub org/repo.
   - Workflow name: `publish.yml`.
   - Environment: leave empty (or use a dedicated environment if you prefer).
   Once configured, the `Publish to PyPI` workflow on tag push will publish without any API token in the repo.
