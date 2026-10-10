import os
from pathlib import Path

from infrastructure.config import CONFIG_ENV

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
DEMO_CONFIGS = sorted(CONFIG_DIR.glob("*.demo.json"))

# main.py loads its configuration at import time; tests that import it run as Hospital A.
os.environ.setdefault(CONFIG_ENV, str(CONFIG_DIR / "hospital-a.demo.json"))
