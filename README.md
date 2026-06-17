# jarvis-settings-server

> **Deprecation candidate — do not extend.**
>
> This service is **superseded by jarvis-config-service** (`/v1/settings/*` on port 7700),
> which exposes the same surface (aggregate, get-by-service, update-by-key) with superuser
> JWT auth. Nothing in the stack currently calls jarvis-settings-server — it is registered,
> deployed, and unused. For new work, use config-service. Do not migrate consumers here or
> add features; if you find a bug while it is still deployed, fix it minimally and move on.

## Purpose

Stateless settings aggregator. Fans out HTTP calls to every registered service's
`/settings/*` endpoint (the standard mount via `jarvis-settings-client`) and aggregates
the results. Mirrors config-service's settings gateway, plus a `?category=X` GET filter
and a `GET /v1/settings/{service_name}/url` debug helper. No database — pure proxy.

### Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/settings/` | Aggregate from all services. `?service=X`, `?category=Y` filters |
| GET | `/v1/settings/{service_name}` | Single service |
| PUT | `/v1/settings/{service_name}/{key}` | Update — proxies to the service's `/settings/{key}` |
| GET | `/v1/settings/{service_name}/url` | Resolved settings URL for the service (debug) |
| GET | `/health` | Health check (no auth) |

All endpoints except `/health` require a **superuser JWT**.

## Running

```bash
# Install (with dev extras for tests)
pip install -e ".[dev]"

# Run the API server (defaults to 0.0.0.0:7708)
python -m app.main
# or
uvicorn app.main:app --host 0.0.0.0 --port 7708

# Tests
pytest

# Docker (dev)
docker compose -f docker-compose.dev.yaml up
```

## Environment

Copy `.env.example` to `.env` and fill in values.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `JARVIS_CONFIG_URL` | yes | `http://localhost:7700` | Service discovery |
| `JARVIS_AUTH_SECRET_KEY` | yes | — | Must match jarvis-auth `AUTH_SECRET_KEY` — validates JWTs locally |
| `JARVIS_AUTH_ALGORITHM` | no | `HS256` | JWT algorithm (match jarvis-auth) |
| `SERVICE_TIMEOUT` | no | `10.0` | Per-service fan-out HTTP timeout |
| `HOST` / `PORT` | no | `0.0.0.0` / `7708` | API server bind |
| `JARVIS_APP_ID` / `JARVIS_APP_KEY` | no | — | Remote logging to jarvis-logs (skipped if key unset) |
| `JARVIS_LOG_CONSOLE_LEVEL` | no | `INFO` | Console log level |
| `JARVIS_LOG_REMOTE_LEVEL` | no | `DEBUG` | Remote log level |
