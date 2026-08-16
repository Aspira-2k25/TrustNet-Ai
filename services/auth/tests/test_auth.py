import pytest
import uuid
import httpx
from services.auth.app.main import app
from services.auth.app.database.session import init_db

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.anyio
async def test_register_success(client):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "SecurePassword123!",
        "role": "user"
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    
    body = response.json()
    assert body["error"] is None
    assert body["data"]["email"] == unique_email
    assert body["data"]["role"] == "user"
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["expires_in"] > 0

@pytest.mark.anyio
async def test_register_duplicate_email(client):
    unique_email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "SecurePassword123!",
        "role": "user"
    }
    # First registration
    res1 = await client.post("/auth/register", json=payload)
    assert res1.status_code == 201
    
    # Second registration with identical email
    res2 = await client.post("/auth/register", json=payload)
    assert res2.status_code == 409
    body = res2.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"

@pytest.mark.anyio
async def test_login_success(client):
    unique_email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"
    
    # Register first
    await client.post("/auth/register", json={"email": unique_email, "password": password})
    
    # Login
    response = await client.post("/auth/login", json={"email": unique_email, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["email"] == unique_email
    assert "access_token" in body["data"]

@pytest.mark.anyio
async def test_login_invalid_password(client):
    unique_email = f"invalid_pw_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/auth/register", json={"email": unique_email, "password": "OriginalPassword123!"})
    
    response = await client.post("/auth/login", json={"email": unique_email, "password": "WrongPassword!"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"

@pytest.mark.anyio
async def test_login_nonexistent_user(client):
    response = await client.post("/auth/login", json={"email": "nonexistent@example.com", "password": "AnyPassword123!"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"

@pytest.mark.anyio
async def test_refresh_token_success(client):
    unique_email = f"refresh_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = await client.post("/auth/register", json={"email": unique_email, "password": "Password123!"})
    refresh_token = reg_res.json()["data"]["refresh_token"]
    
    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert "access_token" in body["data"]
    assert body["data"]["token_type"] == "bearer"

@pytest.mark.anyio
async def test_refresh_token_invalid(client):
    response = await client.post("/auth/refresh", json={"refresh_token": "invalid.jwt.token"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_TOKEN"

@pytest.mark.anyio
async def test_get_current_user_me(client):
    unique_email = f"me_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = await client.post("/auth/register", json={"email": unique_email, "password": "Password123!", "role": "researcher"})
    access_token = reg_res.json()["data"]["access_token"]
    
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["email"] == unique_email
    assert body["data"]["role"] == "researcher"
    assert body["data"]["is_active"] is True

@pytest.mark.anyio
async def test_get_current_user_me_unauthorized(client):
    response = await client.get("/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_TOKEN"
