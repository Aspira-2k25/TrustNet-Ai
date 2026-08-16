# API Gateway Service

The **API Gateway** acts as the perimeter shield and routing proxy for the TRUST[NET] architecture.

## Technology Stack
- **Framework**: FastAPI, Python 3.10+
- **Security**: JWT Bearer Tokens, Bcrypt
- **HTTP Client**: `httpx` (for async microservice proxying)

## The Logic
Instead of the React frontend communicating directly with 4 different backend microservices on different ports, it talks exclusively to the Gateway on Port `8000`.

1. **Authentication Interceptor**: The `auth_middleware.py` intercepts incoming requests, validates JWT tokens against the Auth Service, and blocks unauthorized access.
2. **Reverse Proxying**: When the UI uploads an image to `/api/v1/scans/analyze`, the Gateway streams the multipart form data directly to the **Scan Management Service**, which handles Kafka event generation.
3. **Polling/Telemetry Retrieval**: Once the image is processed, the UI asks the Gateway for the result. The Gateway fetches the final synthesized report from the **Trust Engine Service**.

## Running the Service
```bash
uvicorn gateway.app.main:app --port 8000 --reload
```
