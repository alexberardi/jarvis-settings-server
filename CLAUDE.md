# jarvis-settings-server

Centralized settings aggregator for Jarvis microservices. Acts as a proxy to fetch and update settings across all services.

## Quick Reference

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env and set JARVIS_AUTH_SECRET_KEY (must match jarvis-auth)

# Run
uvicorn app.main:app --reload --port 7708

# Run with Docker
docker-compose up --build

# Test
pytest
pytest --cov=app --cov-report=term-missing
```

## Architecture

```
jarvis-settings-server (proxy, no local DB)
    │
    ├── GET /v1/settings/            → Aggregate from all services
    ├── GET /v1/settings/{service}   → Settings from one service
    └── PUT /v1/settings/{service}/{key} → Update setting
                │
                ▼
        ┌───────────────────┐
        │ jarvis-config-    │  (service discovery)
        │ service :7700     │
        └───────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
jarvis-auth  jarvis-llm   jarvis-*
 /settings   /settings    /v1/settings
```

## Authentication

**Superuser JWT only** - This service only accepts superuser JWT tokens.

1. Login to jarvis-auth as a superuser user
2. Use the JWT in Authorization header: `Bearer <token>`
3. The token must have `is_superuser: true` claim

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/settings/` | Aggregate settings from all services |
| GET | `/v1/settings/?service=jarvis-auth` | Filter to specific service |
| GET | `/v1/settings/?category=model` | Filter by category |
| GET | `/v1/settings/{service}` | Get settings from one service |
| PUT | `/v1/settings/{service}/{key}` | Update a setting |
| GET | `/v1/settings/{service}/url` | Get settings URL for a service |
| GET | `/health` | Health check |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 7708 | Server port |
| `HOST` | No | 0.0.0.0 | Server host |
| `JARVIS_CONFIG_URL` | No | http://localhost:7700 | Config service URL |
| `JARVIS_AUTH_SECRET_KEY` | **Yes** | - | Must match jarvis-auth SECRET_KEY |
| `JARVIS_AUTH_ALGORITHM` | No | HS256 | JWT algorithm |
| `SERVICE_TIMEOUT` | No | 10.0 | HTTP timeout (seconds) |

## Service Settings Path Mapping

All services use `/settings` by default (jarvis-settings-client convention).
Override in `SETTINGS_PATHS` dict only if a service uses a non-standard path.

**Excluded services** (no settings endpoint or self-referential):
- `jarvis-settings-server` (self — would create circular request)
- `jarvis-mcp` (no settings endpoint)
- `jarvis-config-service` (no settings endpoint)

## Dependencies

**Python Libraries:**
- FastAPI, httpx, pydantic
- python-jose (JWT validation)

**Service Dependencies:**
- ✅ **Required**: `jarvis-config-service` (7700) - Service discovery
- ✅ **Required**: `jarvis-auth` (7701) - JWT secret must match for token validation
- ⚠️ **Optional**: All jarvis services with `/settings` or `/v1/settings` endpoints

**Used By:**
- `jarvis-admin` - Web UI for settings management

**Impact if Down:**
- ❌ No settings management via web UI
- ✅ Services continue with existing settings
- ✅ Settings can still be changed via env vars or direct service calls

## Example Usage

```bash
# Get all settings (requires superuser token)
curl -H "Authorization: Bearer <superuser-jwt>" \
     http://localhost:7708/v1/settings/

# Get settings from jarvis-auth only
curl -H "Authorization: Bearer <superuser-jwt>" \
     http://localhost:7708/v1/settings/jarvis-auth

# Update a setting on jarvis-llm-proxy-api
curl -X PUT \
     -H "Authorization: Bearer <superuser-jwt>" \
     -H "Content-Type: application/json" \
     -d '{"value": "new-value"}' \
     http://localhost:7708/v1/settings/jarvis-llm-proxy-api/model.name
```

## Creating a Superuser

```bash
# Using jarvis-auth admin endpoint (requires app-to-app auth)
curl -X PUT \
     -H "X-Jarvis-App-Id: your-app-id" \
     -H "X-Jarvis-App-Key: your-app-key" \
     -H "Content-Type: application/json" \
     -d '{"is_superuser": true}' \
     http://localhost:7701/admin/users/1/superuser
```

## Project Structure

```
jarvis-settings-server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings from env vars
│   ├── auth.py              # Superuser JWT authentication
│   ├── schemas.py           # Pydantic models
│   ├── routes/
│   │   ├── __init__.py
│   │   └── settings.py      # Settings aggregation endpoints
│   └── services/
│       ├── __init__.py
│       ├── service_discovery.py  # Get services from config-service
│       └── settings_proxy.py     # Proxy to individual services
├── tests/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── CLAUDE.md
```
