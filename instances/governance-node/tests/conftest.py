from datetime import datetime
from pathlib import Path

DEMO_DATA = Path(__file__).resolve().parents[3] / "demo-data"
# The demo dataset's reference date.
DEMO_NOW = datetime.fromisoformat("2026-10-10T10:00:00+01:00")
