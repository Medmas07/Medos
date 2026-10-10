"""Port exposing only hospital-local facts to the installed research executor."""

from typing import Protocol

from domain.research_execution import ResearchSubject


class ResearchDataSource(Protocol):
    node_ref: str
    organization_ref: str
    mocked: bool

    def research_subjects(self) -> tuple[ResearchSubject, ...]: ...
