from collections.abc import Callable
from datetime import datetime

from application.authorization_verifier import AuthorizationVerifier
from application.clinical_repository import ClinicalRepository
from domain.patient_history import HistoryQuery, PatientHistory, within_scope


class AuthorizationDenied(Exception):
    """Nothing is disclosed, and nothing says whether the patient is known here."""


def get_patient_history(
    query: HistoryQuery,
    repository: ClinicalRepository,
    verifier: AuthorizationVerifier,
    clock: Callable[[], datetime],
) -> PatientHistory:
    now = clock()
    # Checked before the repository is read, so a refusal cannot depend on the patient.
    if not verifier.allows(query, now):
        raise AuthorizationDenied()
    # Audit of each query (query_id, requester, purpose, scope, basis) is PLANNED: HC-116.
    return PatientHistory(
        query_id=query.query_id,
        patient_ref=query.patient_ref,
        records=within_scope(
            repository.patient_records(query.patient_ref), query.scope
        ),
        mocked=repository.summary().mocked,
        answered_at=now,
    )
