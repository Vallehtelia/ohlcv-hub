# 2026-02-21: Dev pin for filelock / split extras for pip-audit

## What changed

- **Split optional dependencies**: `dev` extra now contains only pytest and bandit (no pip-audit, no filelock). A separate `audit` extra contains `pip-audit` and `filelock>=3.20.3`, both guarded with `python_version>="3.10"`.
- **CI**: Install `.[dev]` and run pytest + bandit on all matrix versions (3.9–3.12). After that, `pip check` runs. On Python 3.10+ only, install `.[audit]` and run pip-audit.
- **No direct filelock pin on 3.9**: On 3.9, `pip install -e ".[dev]"` does not pull in filelock or pip-audit; the audit stack is only installed where it is compatible (3.10+).

## Why

CI was failing on pip-audit because of a vulnerable transitive filelock (3.19.1). pip-audit’s dependency stack (including fixed filelock 3.20.3+) requires Python 3.10+. To keep 3.9 support without fragile transitive pins:

- **dev**: Tools that support 3.9 (pytest, bandit). `pip install -e ".[dev]"` succeeds on 3.9–3.12.
- **audit**: pip-audit and filelock pin only for 3.10+, so audit runs only on Python 3.10+ in CI. No reference to a filelock version for 3.9. Runtime dependencies are unchanged.
