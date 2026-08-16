# API Gateway Service (gateway)

FastAPI gateway that acts as Trust Net's perimeter.

## Responsibilities

- Provides a unified API entrypoint for frontend clients.
- Proxies auth routes to Auth Service.
- Proxies scan routes to Scan Management Service.
- Enforces auth dependency for scan routes.
- Applies rate limiting middleware.
- Handles CORS for local frontend origins.

## Runtime Defaults

- Port: `8000`
- Health endpoint: `GET /health`
- OpenAPI docs: `/docs`

## Proxied Route Prefixes

- `/api/v1/auth/**` -> Auth Service (`http://localhost:8001` by default)
- `/api/v1/scans/**` -> Scan Management Service (`http://localhost:8002` by default)

## Important Files

- `app/main.py` - app bootstrap and middleware wiring
- `app/routers/auth_routes.py` - auth proxy router
- `app/routers/scan_routes.py` - scan proxy router
- `app/middleware/auth_middleware.py` - JWT validation dependency
- `app/middleware/rate_limiter.py` - request throttling

## Run Locally

```bash
pip install -r gateway/requirements.txt
uvicorn gateway.app.main:app --port 8000 --reload
```

## Configuration

Environment variables (defaults in `app/config/settings.py`):

- `AUTH_SERVICE_URL` (default `http://localhost:8001`)
- `SCAN_SERVICE_URL` (default `http://localhost:8002`)
- `TRUST_ENGINE_SERVICE_URL` (default `http://localhost:8004`)
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `RATE_LIMIT_PER_MINUTE`

## Tests

```bash
python -m pytest gateway/tests -v
```
