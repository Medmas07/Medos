"""ReviewerDirectory over the fictional people of demo-data/people.json (HC-131).

Who a reviewer_ref names, with their role and organization: staff and clinicians only,
never patients or relatives. The reference is declared by the caller, not
authenticated: identity and authentication are PLANNED.
"""

import json
from pathlib import Path

from domain.hospital_approval import Reviewer


class FixtureReviewerDirectory:
    def __init__(self, reviewers: list[Reviewer]) -> None:
        self._reviewers = {r.person_ref: r for r in reviewers}

    @classmethod
    def load(cls, path: Path) -> "FixtureReviewerDirectory":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("fictional") is not True:
            raise RuntimeError(f"{path} is not marked fictional")
        return cls(
            [
                Reviewer(p["id"], p["role"], p["organizationId"])
                for group in ("staff", "clinicians")
                for p in data[group]
            ]
        )

    def reviewer(self, person_ref: str) -> Reviewer | None:
        return self._reviewers.get(person_ref)
