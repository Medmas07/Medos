import uuid
from collections.abc import Callable
from datetime import datetime

from application.audit_log import AuditLog
from application.authorization_verifier import AuthorizationVerifier
from application.clinical_repository import ClinicalRepository
from domain.audit_event import AuditEvent, AuditOutcome
from domain.patient_history import HistoryQuery, PatientHistory, within_scope


class AuthorizationDenied(Exception):
    """Nothing is disclosed, and nothing says whether the patient is known here."""


def _new_event_id() -> str:
    return str(uuid.uuid4())


def get_patient_history(
    query: HistoryQuery,
    repository: ClinicalRepository,
    verifier: AuthorizationVerifier,
    audit_log: AuditLog,
    clock: Callable[[], datetime],
    new_event_id: Callable[[], str] = _new_event_id,
) -> PatientHistory:
    now = clock()
    # Checked before the repository is read, so a refusal cannot depend on the patient.
    if not verifier.allows(query, now):
        audit_log.record(
            AuditEvent.of_query(new_event_id(), now, query, AuditOutcome.DENIED)
        )
        raise AuthorizationDenied()
    records = within_scope(repository.patient_records(query.patient_ref), query.scope)
    # No audit, no disclosure: if recording fails, the error propagates and nothing
    # is returned.
    audit_log.record(
        AuditEvent.of_query(
            new_event_id(),
            now,
            query,
            AuditOutcome.DISCLOSED,
            tuple(
                r.record_ref
                for r in records.encounters + records.medications + records.lab_reports
            ),
        )
    )
    return PatientHistory(
        query_id=query.query_id,
        patient_ref=query.patient_ref,
        records=records,
        mocked=repository.summary().mocked,
        answered_at=now,
    )
