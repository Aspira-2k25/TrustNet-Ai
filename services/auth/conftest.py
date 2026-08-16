import sys
from pathlib import Path

# Add services/auth to sys.path so app.* imports work both when running from root and inside the service folder
auth_dir = Path(__file__).resolve().parent
if str(auth_dir) not in sys.path:
    sys.path.insert(0, str(auth_dir))
