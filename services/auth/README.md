# Auth Service (`services/auth/`)

## 📌 Service Overview
The `auth_service` manages user identity, authentication, credential validation, and JWT lifecycle for the TrustNet AI Platform.

---

## 🔑 Key Capabilities
- **Registration**: `/auth/register` (email format validation, bcrypt password hashing with unique salt).
- **Login**: `/auth/login` (verifies credentials, returns short-lived access JWT and refresh JWT).
- **Token Refresh**: `/auth/refresh` (exchanges valid refresh token for a new access token).
- **User Profile**: `/auth/me` (returns current user context).
- **Zero-Network-Call Token Verification**: Employs [`shared/auth/verify_token.py`](../../shared/auth/verify_token.py) so downstream services verify tokens locally using asymmetric/shared secret without making round-trip RPC calls to Auth Service.

---

## 🛠️ Configuration
- `DATABASE_URL`: SQLAlchemy connection string (PostgreSQL in production, SQLite in development).
- `JWT_SECRET_KEY`: Secret used for signing and verifying tokens.
- `JWT_ALGORITHM`: `HS256`.
- `JWT_ACCESS_EXPIRY_MINUTES`: `30`.

---

## 🧪 Testing
```bash
python -m pytest services/auth/tests/ -v
```
