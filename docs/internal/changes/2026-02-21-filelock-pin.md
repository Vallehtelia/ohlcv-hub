# 2026-02-21: Dev pin for filelock / split extras for pip-audit

## What changed

- **Split optional dependencies**: `dev` extra now contains only pytest and bandit (no pip-audit, no filelock). A separate `audit` extra contains `pip-audit` and `filelock>=3.20.3`, both guarded with `python_version>="3.10"`.
- **CI**: Install `.[dev]` and run pytest + bandit on all matrix versions (3.9–3.12). After that, `pip check` runs. On Python 3.10+ only, install `.[audit]` and run pip-audit.
- **No direct filelock pin on 3.9**: On 3.9, `pip install -e ".[dev]"` does not pull in filelock or pip-audit; the audit stack is only installed where it is compatible (3.10+).

## Why

CI was failing on pip-audit because of a vulnerable transitive filelock (3.19.1). pip-audit is separated into the **audit** extra and runs only on Python 3.10+ in CI: the toolchain and transitive dependencies (including a fixed filelock 3.20.3+) require Python 3.10+; on 3.9 we do not install or run pip-audit, so 3.9 dependency resolution cannot fail on audit stack. Runtime dependencies are unaffected.

- **dev**: pytest and bandit only; `pip install -e ".[dev]"` succeeds on 3.9–3.12.
- **audit**: pip-audit (and optional filelock pin) with `python_version>="3.10"`; installed and run only on 3.10+ in CI. No filelock or pip-audit requirement exists for python<3.10.
