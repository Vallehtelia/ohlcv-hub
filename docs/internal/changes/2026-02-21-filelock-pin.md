# 2026-02-21: Dev pin for filelock to satisfy pip-audit

## What changed

Added dev dependency pins for filelock under `[project.optional-dependencies].dev` with environment markers:

- `filelock>=3.20.3; python_version>="3.10"`
- `filelock>=3.19.2; python_version<"3.10"`

CI runs pip-audit only on Python 3.10+ (skipped on 3.9).

## Why

CI was failing on the pip-audit step because a transitive dependency (filelock 3.19.1) was reported as vulnerable. filelock is pulled in indirectly (e.g. by pip-audit’s dependency chain). Pinning filelock in the dev extras ensures resolved environments use a patched version.

The marker split is needed because filelock 3.20.x requires Python 3.10+; on 3.9 we pin `>=3.19.2` (patched for the known issue) so `pip install -e ".[dev]"` still succeeds. pip-audit is skipped on Python 3.9 in CI because the fixed filelock versions that satisfy pip-audit (3.20.3+) are not available on 3.9; tests and bandit still run on 3.9. Runtime dependencies were not changed.
