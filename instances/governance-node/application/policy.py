"""Governance policy use cases (HC-135): read the policy versions and their status."""

from datetime import datetime

from domain.policy import GovernancePolicy, PolicyHistory, PolicyStatus


class PolicyNotFound(Exception):
    pass


def list_policies(
    policies: PolicyHistory, now: datetime
) -> list[tuple[GovernancePolicy, PolicyStatus]]:
    """Every version with its status now, the latest version first."""
    return [(p, policies.status_at(p, now)) for p in reversed(policies.versions)]


def get_policy(
    policy_ref: str, policies: PolicyHistory, now: datetime
) -> tuple[GovernancePolicy, PolicyStatus]:
    policy = policies.policy(policy_ref)
    if policy is None:
        raise PolicyNotFound(policy_ref)
    return policy, policies.status_at(policy, now)
