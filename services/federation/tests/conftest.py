from datetime import datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

# Inside grant-a-drx's validity; the demo dataset's reference date.
DEMO_NOW = datetime.fromisoformat("2026-10-10T10:00:00+01:00")

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "federation"
DEMO_SEED = Path(__file__).resolve().parents[1] / "registry-seed.demo.json"


def contract(name: str) -> dict:
    return yaml.safe_load((CONTRACTS / name).read_text())


def validator(document: dict, schema_name: str) -> Draft202012Validator:
    schema = {
        "$ref": f"#/components/schemas/{schema_name}",
        "components": document["components"],
    }
    return Draft202012Validator(schema, format_checker=FormatChecker())
