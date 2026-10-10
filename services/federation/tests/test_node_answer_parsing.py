import copy
from datetime import datetime

import pytest

from adapters.outbound.hospital_node_contract import InvalidNodeAnswer, answer_from_wire
from domain.federated_query import (
    Authorization,
    AuthorizationBasis,
    NodeQuery,
    NodeRef,
    RecordType,
    Requester,
    ScopeItem,
)
from tests.conftest import contract

NODE_CONTRACT = contract("hospital-node-federation.v1.yaml")
EXAMPLES = NODE_CONTRACT["paths"]["/v1/federation/queries"]["post"]["responses"]["200"][
    "content"
]["application/json"]["examples"]
FOUND = EXAMPLES["medicationFound"]["value"]
B = NodeRef("org-hospital-b", "node-hospital-b")
QUERY = NodeQuery(
    query_id=FOUND["query_id"],
    patient_ref="pat-a",
    scope=frozenset({ScopeItem.MEDICATIONS}),
    purpose="Consultation de cardiologie",
    requested_by=Requester("org-hospital-a", "clin-x"),
    authorization=Authorization(
        AuthorizationBasis.PATIENT_ACCESS_GRANT,
        "grant-a-drx",
        datetime.fromisoformat("2026-10-24T09:00:00+01:00"),
    ),
)


def changed(mutate):
    copied = copy.deepcopy(FOUND)
    mutate(copied)
    return copied


def test_parses_the_contract_example_and_keeps_the_node_provenance():
    answer = answer_from_wire(B, QUERY, FOUND)
    assert answer.mocked is True
    [entry] = answer.entries
    assert (entry.entry_ref, entry.record_type, entry.source) == (
        "med-b-leila-coagulix",
        RecordType.MEDICATION,
        B,
    )
    assert entry.details == FOUND["entries"][0]["medication"]


def test_nothing_disclosed_is_an_empty_answer():
    value = EXAMPLES["nothingDisclosed"]["value"]
    a = NodeRef("org-hospital-a", "node-hospital-a")
    assert answer_from_wire(a, QUERY, value).entries == ()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(query_id="another-query"),
        lambda r: r.update(patient_ref="pat-b"),
        lambda r: r.update(node_ref="node-hospital-a"),
        lambda r: r["entries"][0]["source"].update(node_ref="node-hospital-a"),
        lambda r: r["entries"][0].update(record_type="encounter"),
        lambda r: r["entries"][0]["medication"].update(patient_name="Leïla"),
        lambda r: r.update(raw_record={"x": 1}),
        lambda r: r["entries"][0].update(occurred_at="2026-05-20T00:00:00"),
        lambda r: r.update(contract_version="2.0"),
        lambda r: r["entries"][0]["medication"].update(status="maybe"),
        lambda r: r["entries"][0].update(entry_ref="Leïla Mansouri"),
        lambda r: r["provenance"].update(mocked="no"),
    ],
    ids=[
        "other_query",
        "other_patient",
        "other_node",
        "foreign_entry",
        "body_mismatch",
        "extra_field_in_body",
        "extra_top_level_field",
        "naive_datetime",
        "unknown_contract_version",
        "unknown_status",
        "name_as_ref",
        "mocked_not_bool",
    ],
)
def test_anything_outside_the_contract_or_the_question_is_rejected(mutate):
    with pytest.raises(InvalidNodeAnswer):
        answer_from_wire(B, QUERY, changed(mutate))


def test_entries_outside_the_requested_scope_are_rejected():
    lab_only = NodeQuery(
        **{**QUERY.__dict__, "scope": frozenset({ScopeItem.LAB_REPORTS})}
    )
    with pytest.raises(InvalidNodeAnswer, match="outside the scope"):
        answer_from_wire(B, lab_only, FOUND)
