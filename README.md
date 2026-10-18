# life-health-api
The Health cell: its own API (Railway, serverless) and its own Neon
database, described by `cell.yaml` and served by the code in `src/cellkit/`, which
this repository owns. It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `life-health-api`, service `health-api` (Serverless) |
| Data | Neon project `life-health-api`, database `health` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`health`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `health.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/health-metrics` | health-metric | — |

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/health-db provision
npm install && railway config apply   # service settings only; code deploys from GitHub (below)
railway scale --service health-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Deploys (CD, since 2026-10-18): `health-api` is connected to this repository's `main` with
Railway's Wait for CI (`checkSuites`). A merge to `main` deploys only after the CI and security
checks pass; a failing check leaves production on the previous deployment. Roll back by
redeploying an earlier deployment in Railway. `railway up` is no longer used.

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see
`src/cellkit/_sentry.py`), `HEALTH_DB_MODE=hosted`, `HEALTH_DB_URL_API`,
`HEALTH_JWT_PUBLIC_KEY_PEM`, `HEALTH_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`.
