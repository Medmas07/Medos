from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "api"


def load(relative_path: str) -> dict:
    return yaml.safe_load((CONTRACTS / relative_path).read_text())


def validator(contract: dict, ref: str) -> Draft202012Validator:
    schema = {"$ref": ref, "components": contract["components"]}
    return Draft202012Validator(schema, format_checker=FormatChecker())
