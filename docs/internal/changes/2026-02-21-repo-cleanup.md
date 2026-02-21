# 2026-02-21: Repo cleanup for public release

## What changed

- **README.md** rewritten for end users: title + description, Features, Quickstart (install, env, example commands), Output + schema table, Notes/Limitations (MVP), minimal Development (no publishing). Removed PyPI/tag instructions.
- **.gitignore** extended with `.mypy_cache/`, `.ruff_cache/`, `validation_report.json`. `.venv/`, `venv/`, `env/`, and other common Python artifacts were already present.
- **Docs layout**: All internal markdown moved under `docs/internal/`:
  - `docs/changes/*` → `docs/internal/changes/*`
  - `docs/llm-handoff/*` → `docs/internal/llm-handoff/*`
  - `docs/process.md` → `docs/internal/process.md`
  - Added `docs/internal/README.md` describing internal docs.

## Files moved

- From `docs/changes/`: all `2026-02-20-*.md` and `2026-02-20-*.md` → `docs/internal/changes/`
- From `docs/llm-handoff/`: all `*.md` → `docs/internal/llm-handoff/`
- `docs/process.md` → `docs/internal/process.md`

(Empty `docs/changes/` and `docs/llm-handoff/` directories may remain; they can be removed if desired.)

## New README outline

1. Title + one-paragraph description  
2. Features (bullets)  
3. Quickstart: install (PyPI + dev), env vars, example commands  
4. Output: file names, validation_report, schema table  
5. Notes / Limitations (MVP)  
6. Development: pytest, bandit, pip-audit; pointer to docs/internal  
7. License  

## How to verify

- `pytest -q` — all tests pass.
- `pip install -e ".[dev]"` — install works.
- `python -m build` (optional) — build succeeds.
- No references to `docs/changes/` or `docs/llm-handoff/` or `docs/process.md` in README; workflows do not reference moved paths.
