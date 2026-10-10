"""The governance policy versions, read from fictional demo data at startup (HC-135).

The Governance Node's own rules, as data: demo-data/governance.json holds each version
of the fictional demo policy. They are read once, validated, and never changed while the
Node runs; publishing a new version means adding it to the file and restarting. How the
Authority writes and approves a new version is OPEN. A file not marked fictional, or a
policy that breaks the rules of domain/policy.py, stops startup.
"""

import json
from datetime import datetime
from pathlib import Path

from adapters.outbound.in_memory_hospital_applications import SeedError
from domain.policy import ConsentMode, GovernancePolicy, InvalidPolicy, PolicyHistory


def load_policies(path: Path) -> PolicyHistory:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("fictional") is not True:
            raise SeedError(f"{path} is not marked fictional")
        return PolicyHistory(tuple(_policy(raw) for raw in data["policies"]))
    except SeedError:
        raise
    except InvalidPolicy as error:
        raise SeedError(f"Invalid governance policy in {path}: {error}") from error
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise SeedError(f"Cannot load governance policies {path}: {error}") from error


def _policy(raw: dict) -> GovernancePolicy:
    sync, research = raw["synchronization"], raw["research"]
    return GovernancePolicy(
        policy_ref=raw["id"],
        version=raw["version"],
        effective_from=datetime.fromisoformat(raw["effectiveAt"]),
        title=raw["title"],
        minimum_rationale_length=raw["review"]["minimumRationaleLength"],
        maximum_sync_duration_days=sync["maximumDurationDays"],
        consent_bases=tuple(
            (basis, ConsentMode(mode)) for basis, mode in sync["consentBases"].items()
        ),
        maximum_research_validity_months=research["maximumValidityMonths"],
        minimum_cell_size=research["minimumCellSize"],
    )
