"""Every API and Federation contract is valid OpenAPI and every example matches its schema."""

import pytest
import yaml
from openapi_spec_validator import validate

from conftest import CONTRACTS, EVENTS, FEDERATION, validator

CONTRACT_FILES = sorted(
    [
        *CONTRACTS.rglob("*.v*.yaml"),
        *FEDERATION.rglob("*.v*.yaml"),
        *EVENTS.rglob("*.v*.yaml"),
    ]
)


HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _deref(contract: dict, node: dict) -> dict:
    """Follow a local `$ref` such as `#/components/responses/InvalidRequest`."""
    while "$ref" in node:
        target = contract
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def _examples(contract: dict):
    for path, item in contract["paths"].items():
        for method, operation in item.items():
            if method not in HTTP_METHODS:
                continue
            request = _deref(contract, operation.get("requestBody", {}))
            bodies = [("request", request.get("content", {}))]
            bodies += [
                (status, _deref(contract, response).get("content", {}))
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
