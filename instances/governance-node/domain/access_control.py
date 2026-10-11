"""What each role may do at the Governance Node (HC-212, ADR-0011).

A fixed role-to-permission matrix, denying by default: a role absent from it, or a
permission it does not list, grants nothing. Roles are those of the fictional demo
people (demo-data/people.json); patients and relatives never act here. Which
organization a person may act for is domain/organization_identity.py's (HC-213).
"""

from enum import Enum


class Permission(str, Enum):
    # Read the applications and requests under review, and record decisions on them.
    REVIEW = "governance:review"
    # Read the Node's audit trail and the ledger proofs anchoring it.
    AUDIT = "governance:audit"
    # Submit a synchronization request between two organizations.
    REQUEST_SYNCHRONIZATION = "synchronization:request"
    # Submit a research access request for a project.
    REQUEST_RESEARCH = "research:request"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "governance_reviewer": frozenset({Permission.REVIEW, Permission.AUDIT}),
    "hospital_manager": frozenset({Permission.REQUEST_SYNCHRONIZATION}),
    # A physician asks for a patient's history held by another organization.
    "physician": frozenset({Permission.REQUEST_SYNCHRONIZATION}),
    "researcher": frozenset({Permission.REQUEST_RESEARCH}),
}


class PermissionDenied(Exception):
    def __init__(self, role: str, permission: Permission) -> None:
        super().__init__(f"The role {role} does not grant {permission.value}.")
        self.role = role
        self.permission = permission


def permissions_of(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def check_permission(role: str, permission: Permission) -> None:
    if permission not in permissions_of(role):
        raise PermissionDenied(role, permission)
