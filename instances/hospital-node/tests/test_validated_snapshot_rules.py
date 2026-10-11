import json

import pytest

from adapters.outbound.validated_snapshot_rules import (
    ONC_HIGH_PRIORITY_2012,
    SnapshotError,
    ValidatedSnapshotRuleSource,
)
from domain.medication_safety import (
    Medication,
    MedicationStatement,
    SafetySourceKind,
    Severity,
    StatementSource,
    StatementStatus,
    UnevaluatedReason,
    check_interactions,
)

SNAPSHOT = json.loads(ONC_HIGH_PRIORITY_2012.read_text(encoding="utf-8"))
RULES = ValidatedSnapshotRuleSource.load(ONC_HIGH_PRIORITY_2012).rule_set()


def check(proposed, *current):
    statements = tuple(
        MedicationStatement(
            f"s-{i}",
            Medication(name),
            StatementStatus.ACTIVE,
            StatementSource("org-hospital-a"),
        )
        for i, name in enumerate(current)
    )
    return check_interactions(RULES, Medication(proposed), statements)


def test_the_onc_snapshot_is_a_validated_source_and_not_mocked():
    source = ValidatedSnapshotRuleSource.load(ONC_HIGH_PRIORITY_2012)

    assert source.mocked is False
    assert (RULES.kind, RULES.name, RULES.version) == (
        SafetySourceKind.VALIDATED_SOURCE,
        "onc-high-priority-ddi",
        "2012-table2/hc-163-1",
    )
    assert {r.severity for r in RULES.rules} == {Severity.CONTRAINDICATED}
    assert all("doi:10.1136/amiajnl-2011-000612" in r.reference for r in RULES.rules)
    assert "non exhaustif" in RULES.scope_note


def test_the_transcription_of_table_2_is_frozen():
    """Member counts per source row, as printed in Table 2 (after documented corrections)."""
    counts = {
        i["sourceRow"]: (len(i["object"]), len(i["precipitant"]))
        for i in SNAPSHOT["interactions"]
    }

    assert counts == {
        3: (12, 5),
        4: (1, 5),
        6: (1, 2),
        8: (11, 5),
        11: (1, 23),
        16: (6, 5),
        22: (1, 4),
        23: (6, 10),
        25: (2, 20),
        27: (15, 4),
        28: (1, 7),
        30: (1, 1),
        31: (3, 5),
    }
    assert len(RULES.rules) == sum(a * b for a, b in counts.values()) == 362
    assert {e["sourceRow"] for e in SNAPSHOT["excluded"]} == {20, 21}


@pytest.mark.parametrize(
    "proposed, current, rule_id",
    [
        ("simvastatin", "clarithromycin", "onc-2012-row-25"),
        # French INN on both sides, any case and accents.
        ("SIMVASTATINE", "clarithromycine", "onc-2012-row-25"),
        ("Clarithromycine", "Simvastatine", "onc-2012-row-25"),
        ("tizanidine", "ciprofloxacine", "onc-2012-row-28"),
        ("rifampicine", "ritonavir", "onc-2012-row-23"),
        ("millepertuis", "darunavir", "onc-2012-row-23"),
        ("St John’s wort", "darunavir", "onc-2012-row-23"),
        ("sumatriptan", "bleu de méthylène", "onc-2012-row-31"),
        ("tranylcypromine", "procarbazine", "onc-2012-row-30"),
    ],
)
def test_a_listed_pair_is_contraindicated(proposed, current, rule_id):
    [warning] = check(proposed, current).warnings

    assert (warning.rule.rule_id, warning.rule.severity) == (
        rule_id,
        Severity.CONTRAINDICATED,
    )


def test_class_members_differ_by_row_as_printed():
    # Row 25's CYP3A4 inhibitors do not include fosamprenavir; row 11's do.
    assert check("simvastatin", "fosamprenavir").warnings == ()
    assert check("irinotecan", "fosamprenavir").warnings != ()
    # Row 27 removed amiodarone from the inhibitors of ergot alkaloids.
    assert check("ergotamine", "amiodarone").warnings == ()


def test_drugs_outside_the_list_are_reported_not_assumed_safe():
    outcome = check(
        "simvastatin",
        "dexlansoprazole",  # named in the panel's notes, not in the final list
        "Zocor",  # a brand name: not matched
        "Coagulix",  # a fictional demo medicine
    )

    assert outcome.warnings == ()
    assert {u.reason for u in outcome.unevaluated} == {
        UnevaluatedReason.NOT_IN_RULE_SOURCE
    }
    assert len(outcome.unevaluated) == 3


def broken(tmp_path, mutate):
    snapshot = json.loads(ONC_HIGH_PRIORITY_2012.read_text(encoding="utf-8"))
    mutate(snapshot)
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "mutate, message",
    [
        (
            lambda s: s["ruleSet"].update(kind="deterministic_rule_set"),
            "not a validated_source",
        ),
        (lambda s: s["ruleSet"].update(kind="llm"), "Invalid"),
        (
            lambda s: s["interactions"].append(dict(s["interactions"][0], id="dup")),
            "repeats",
        ),
        (
            lambda s: s["ingredients"][0]["synonyms"].append("ritonavir"),
            "points to two medications",
        ),
        (lambda s: s["interactions"][0].update(severity="severe"), "Invalid"),
    ],
)
def test_an_inconsistent_snapshot_stops_startup(tmp_path, mutate, message):
    with pytest.raises(SnapshotError, match=message):
        ValidatedSnapshotRuleSource.load(broken(tmp_path, mutate))
