# Auth Service (services/auth)

FastAPI microservice for identity and JWT token lifecycle.

## Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `GET /health`

## Behavior

- Stores users in configured DB (SQLite by default in local dev).
- Hashes passwords (bcrypt via passlib stack).
- Issues access and refresh JWT tokens.
- Validates access token for `/auth/me`.

## Runtime Defaults

- Port: `8001`
- DB default: `sqlite+aiosqlite:///./auth_dev.db`

## Run Locally

```bash
pip install -r services/auth/requirements.txt
uvicorn services.auth.app.main:app --port 8001 --reload
```

## Config Keys

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`

## Tests

```bash
python -m pytest services/auth/tests -v
```
