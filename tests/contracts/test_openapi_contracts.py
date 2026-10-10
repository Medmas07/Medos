"""Every API contract is valid OpenAPI and every example matches its schema."""

import pytest
import yaml
from openapi_spec_validator import validate

from conftest import CONTRACTS, validator

CONTRACT_FILES = sorted(CONTRACTS.rglob("*.v*.yaml"))


def _examples(contract: dict):
    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            bodies = [("request", operation.get("requestBody", {}).get("content", {}))]
            bodies += [
                (status, response.get("content", {}))
                for status, response in operation["responses"].items()
            ]
            for where, content in bodies:
                for media in content.values():
                    for name, example in media.get("examples", {}).items():
                        yield (
                            f"{method.upper()} {path} {where} {name}",
                            media["schema"]["$ref"],
                            example["value"],
                        )


def test_contracts_exist():
    assert CONTRACT_FILES


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_contract_is_valid_openapi(path):
    validate(yaml.safe_load(path.read_text()))


@pytest.mark.parametrize("path", CONTRACT_FILES, ids=lambda p: p.name)
def test_examples_match_their_schemas(path):
    contract = yaml.safe_load(path.read_text())
    for label, ref, value in _examples(contract):
        errors = list(validator(contract, ref).iter_errors(value))
        assert not errors, f"{label}: {errors[0].message}"
