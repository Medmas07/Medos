"""Per-hospital configuration, read from the JSON file named by HOSPITAL_NODE_CONFIG.

One codebase runs as one process per hospital (ADR-0003). A missing, unreadable, or
invalid file stops startup: an instance never falls back to another hospital's identity.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from domain.node_identity import InvalidNodeIdentity, NodeIdentity

CONFIG_ENV = "HOSPITAL_NODE_CONFIG"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class HospitalNodeConfig:
    identity: NodeIdentity
    port: int
    # Local storage location for this hospital only. Nothing reads or writes it until
    # the clinical repository exists (HC-113).
    storage_dir: Path


class _ConfigFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notice: str | None = None
    node_ref: str
    organization_ref: str
    port: int = Field(ge=1024, le=65535)
    storage_dir: str = Field(min_length=1)


def config_path_from_env() -> Path:
    value = os.environ.get(CONFIG_ENV)
    if not value:
        raise ConfigError(
            f"{CONFIG_ENV} is not set. Point it to a hospital configuration file, "
            "for example config/hospital-a.demo.json."
        )
    return Path(value)


def load_config(path: Path) -> HospitalNodeConfig:
    try:
        raw = _ConfigFile.model_validate_json(path.read_text(encoding="utf-8"))
        identity = NodeIdentity(raw.node_ref, raw.organization_ref)
    except OSError as error:
        raise ConfigError(
            f"Cannot read hospital configuration {path}: {error}"
        ) from error
    except (ValidationError, InvalidNodeIdentity) as error:
        raise ConfigError(f"Invalid hospital configuration {path}: {error}") from error
    # A relative storage_dir is resolved against the configuration file, not the CWD.
    return HospitalNodeConfig(
        identity=identity,
        port=raw.port,
        storage_dir=(path.parent / raw.storage_dir).resolve(),
    )
