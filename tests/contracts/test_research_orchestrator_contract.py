"""Boundary rules for the HC-182 Research Job Orchestrator contracts."""

from conftest import load, validator


ORCHESTRATION = load("research/research-job-orchestration.v1.yaml")
AUTHORIZATION = load("research/research-authorization-check.v1.yaml")


def canonical_request():
    return {
        "job_ref": "job-001",
        "project_ref": "proj-001",
        "authorization_decision_ref": "dec-rar-001",
        "requested_by": "usr-aymen",
        "purpose": "Aggregate cardiometabolic risk research",
        "target_organizations": ["org-hospital-a", "org-hospital-b"],
        "data_scope": {
            "population": {"age_min": 40, "age_max": 79},
            "variables": ["age_band", "hba1c"],
        },
        "algorithm": {
            "language": "python",
            "artifact_ref": "notebook://nb-001/cell/nb-001-cell-2",
            "sha256": "7da3c4f53384d2c0bf4e50f736e6e0242e57a77cf18720f62e16c13c49d79801",
            "entrypoint": "compute",
        },
        "output_policy": {
            "kind": "aggregate_table",
            "minimum_cell_size": 10,
            "require_disclosure_review": True,
        },
    }


def test_orchestration_request_reuses_canonical_fictional_refs():
    schema = validator(ORCHESTRATION, "#/components/schemas/JobRequest")
    assert schema.is_valid(canonical_request())


def test_orchestration_request_rejects_raw_output_and_patient_ids():
    schema = validator(ORCHESTRATION, "#/components/schemas/JobRequest")
    raw_output = canonical_request()
    raw_output["output_policy"]["kind"] = "raw_records"
    assert not schema.is_valid(raw_output)

    patient_level = canonical_request()
    patient_level["data_scope"]["population"]["patient_ids"] = ["pat-a"]
    assert not schema.is_valid(patient_level)


def test_governance_decision_carries_scope_and_expiry():
    schema = validator(AUTHORIZATION, "#/components/schemas/AuthorizationDecision")
    decision = {
        "decision_ref": "dec-rar-001",
        "status": "approved",
        "approved_organization_refs": ["org-hospital-a", "org-hospital-b"],
        "approved_variables": ["age_band", "hba1c"],
        "authority_organization_ref": "org-governance",
        "valid_until": "2026-12-31T23:59:59+01:00",
    }
    assert schema.is_valid(decision)
