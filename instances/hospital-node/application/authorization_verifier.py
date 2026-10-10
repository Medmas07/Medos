from datetime import datetime
from typing import Protocol

from domain.patient_history import HistoryQuery


class AuthorizationVerifier(Protocol):
    """Decides whether a query's Governance-backed basis covers it.

    How a node verifies the basis with the Governance Node is OPEN. Implementations deny
    by default: an unknown, expired, revoked, mis-addressed, or narrower basis is refused.
    """

    def allows(self, query: HistoryQuery, at: datetime) -> bool: ...
