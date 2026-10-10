"""Notification Service configuration."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8700
    fixtures_path: Path | None = None
    seed_demo_data: bool = True

    @classmethod
    def from_environment(cls) -> "Settings":
        host = os.environ.get("NOTIFICATION_SERVICE_HOST", "0.0.0.0")
        port = int(os.environ.get("NOTIFICATION_SERVICE_PORT", "8700"))
        fixtures = os.environ.get("NOTIFICATION_FIXTURES_PATH")
        seed = os.environ.get("NOTIFICATION_SEED_DEMO", "true").lower() == "true"

        repo_root = Path(__file__).resolve().parents[3]
        demo_fixtures = repo_root / "demo-data" / "notifications.json"

        resolved_fixtures = Path(fixtures) if fixtures else (demo_fixtures if demo_fixtures.exists() else None)

        return cls(
            host=host,
            port=port,
            fixtures_path=resolved_fixtures,
            seed_demo_data=seed,
        )
