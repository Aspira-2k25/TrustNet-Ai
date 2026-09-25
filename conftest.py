import os

# Set default test environment variables for local testing
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("ALLOW_MOCK_AUTH", "true")
