# 2026-02-21: Dev pin for filelock to satisfy pip-audit

## What changed

Added a dev dependency pin: `filelock>=3.20.3` under `[project.optional-dependencies].dev`.

## Why

CI was failing on the pip-audit step because a transitive dependency (filelock 3.19.1) was reported as vulnerable. filelock is pulled in indirectly (e.g. by pip-audit’s dependency chain, e.g. CacheControl or platformdirs). Pinning `filelock>=3.20.3` in the dev extras ensures the resolved environment uses a patched version so pip-audit passes. Runtime dependencies were not changed; filelock is only needed for the dev/audit tooling.
