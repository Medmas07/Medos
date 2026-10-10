from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2] / "contracts"
CONTRACTS = ROOT / "api"
FEDERATION = ROOT / "federation"
EVENTS = ROOT / "events"


def load(relative_path: str, root: Path = CONTRACTS) -> dict:
    return yaml.safe_load((root / relative_path).read_text())


def validator(contract: dict, ref: str) -> Draft202012Validator:
    schema = {"$ref": ref, "components": contract["components"]}
    return Draft202012Validator(schema, format_checker=FormatChecker())
