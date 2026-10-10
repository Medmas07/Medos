import json
import threading

import pytest

from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.in_memory_hospital_applications import SeedError
from application.audit import record
from domain.audit import AuditAction, AuditDomain, AuditOutcome, SubjectType
from tests.conftest import DEMO_DATA, DEMO_NOW

GOVERNANCE = DEMO_DATA / "governance.json"


def trail() -> InMemoryAuditTrail:
    return InMemoryAuditTrail.load(GOVERNANCE)


def check_event(t: InMemoryAuditTrail):
    return record(
        t,
        DEMO_NOW,
        AuditAction.AUTHORIZATION_CHECKED,
        AuditDomain.SYNCHRONIZATION,
        "clin-x",
        SubjectType.DECISION,
        "dec-sync-001",
        ("org-governance", "org-hospital-a"),
        AuditOutcome.DENIED,
        "not_found",
    )


def test_seeds_the_demo_events_with_domain_and_outcome_from_their_decision():
    t = trail()

    assert [e.event_ref for e in t.events()] == [f"evt-00{n}" for n in range(1, 8)]
    evt_005 = t.event("evt-005")
    assert (evt_005.domain, evt_005.outcome) == (
        AuditDomain.SYNCHRONIZATION,
        AuditOutcome.REJECTED,
    )
    assert t.event("evt-004").domain is AuditDomain.RESEARCH
    assert t.event("evt-006").domain is AuditDomain.HOSPITAL_APPROVAL
    assert t.event("evt-007").actor_ref is None
    assert t.durable is False


def test_appends_with_the_next_reference():
    t = trail()

    assert check_event(t).event_ref == "evt-008"
    assert check_event(t).event_ref == "evt-009"
    assert t.event("evt-009").reason == "not_found"


def test_concurrent_appends_get_distinct_references():
    t = trail()
    threads = [threading.Thread(target=check_event, args=(t,)) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    refs = [e.event_ref for e in t.events()]
    assert len(refs) == len(set(refs)) == 27


def write(tmp_path, change):
    data = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "governance.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(fictional=False),
        lambda d: d["auditEvents"][0].update(subjectId="dec-unknown"),
        lambda d: d["auditEvents"][0].update(at="2025-01-28T11:00:00"),
        lambda d: d["auditEvents"][0].update(action="deleted"),
        lambda d: d["auditEvents"][0].update(organizationIds=[]),
        lambda d: d["auditEvents"].append(d["auditEvents"][0]),
        lambda d: d.pop("auditEvents"),
    ],
)
def test_refuses_an_unusable_seed(tmp_path, change):
    with pytest.raises(SeedError):
        InMemoryAuditTrail.load(write(tmp_path, change))
