"""Research view over this node's visibly MOCKED fictional repository."""

from adapters.outbound.fixture_clinical_repository import FixtureClinicalRepository
from domain.node_identity import NodeIdentity
from domain.research_execution import ResearchSubject


class FixtureResearchDataSource:
    mocked = True

    def __init__(
        self, identity: NodeIdentity, repository: FixtureClinicalRepository
    ) -> None:
        self.node_ref = identity.node_ref
        self.organization_ref = identity.organization_ref
        self.repository = repository

    def research_subjects(self) -> tuple[ResearchSubject, ...]:
        return self.repository.local_research_subjects()
