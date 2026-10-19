import os
import tempfile
from pathlib import Path

# Test collection imports service settings. Isolate persistence before those
# imports, even when a developer's .env points at a live database.
_test_state = Path(tempfile.mkdtemp(prefix="trustnet-tests-"))
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_MOCK_AUTH"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (_test_state / "tests.db").as_posix()
os.environ["STORAGE_DIR"] = str(_test_state / "uploads")
os.environ["KAFKA_ENABLED"] = "false"
