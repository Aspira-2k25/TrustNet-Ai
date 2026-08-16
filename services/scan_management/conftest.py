import sys
from pathlib import Path

scan_dir = Path(__file__).resolve().parent
if str(scan_dir) not in sys.path:
    sys.path.insert(0, str(scan_dir))
