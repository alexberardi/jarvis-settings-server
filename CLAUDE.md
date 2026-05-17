# jarvis-settings-server

> **⚠️ Deprecation candidate — do not extend.**
>
> This service was intended as a standalone settings aggregator at port 7708, but admin and other consumers ended up calling the equivalent endpoints on **jarvis-config-service** (`/v1/settings/*`) directly. As of today, **nothing in the stack calls jarvis-settings-server** — it's registered, deployed, and unused.
>
> **For new work, use `jarvis-config-service /v1/settings/*` (port 7700).** It exposes the same surface (aggregate, get-by-service, update-by-key) with superuser JWT auth.
>
> Don't add features here. Don't migrate consumers here. If you find a bug while it's still deployed, fix it minimally and move on.

---

## What it does (for reference)

Stateless settings aggregator. Fans out HTTP calls to every registered service's `/settings/*` endpoint (the standard mount via `jarvis-settings-client`) and aggregates the results. Mirrors what config-service's settings-gateway does, plus:

- `?category=X` query filter on GET
- `GET /v1/settings/{service_name}/url` debug helper

Otherwise identical.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/settings/` | Aggregate from all services. `?service=X`, `?category=Y` filters available |
| GET | `/v1/settings/{service_name}` | Single service |
| PUT | `/v1/settings/{service_name}/{key}` | Update — proxies to the service's `/settings/{key}` |
| GET | `/v1/settings/{service_name}/url` | Returns the resolved settings URL for the service (debug) |
| GET | `/health` | |

All endpoints (except `/health`) require **superuser JWT**.

## Config surface

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `JARVIS_CONFIG_URL` | yes | `http://localhost:7700` | Service discovery |
| `JARVIS_AUTH_SECRET_KEY` | yes | — | **Must match jarvis-auth `AUTH_SECRET_KEY`** — used to validate JWTs locally |
| `JARVIS_AUTH_ALGORITHM` | no | `HS256` | |
| `SERVICE_TIMEOUT` | no | `10.0` | Per-service fan-out timeout |
| `PORT` / `HOST` | no | `7708` / `0.0.0.0` | |

## Architecture

```
app/
├── main.py                              # FastAPI entry
├── auth.py                              # Superuser JWT validation
├── config.py                            # Env settings
├── schemas.py                           # Pydantic models
├── routes/settings.py                   # /v1/settings/* — same surface as config-service gateway
└── services/
    ├── service_discovery.py             # Reads from jarvis-config-service /services
    └── settings_proxy.py                # Fans out to each service's /settings/*
```

No database. Pure proxy.

## If we ever decide to use it

The cleanest migration would be: update jarvis-admin to point at `${settingsServerUrl}/v1/settings/*` instead of `${configUrl}/v1/settings/*`, then remove the gateway router from jarvis-config-service. Both surfaces are byte-compatible (same path shapes, same JWT auth) — admin would only need to change the URL prefix.

Until that decision is made, treat this service as orphaned.
