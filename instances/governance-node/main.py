import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from adapters.inbound.http.audit_events import create_router as create_audit_router
from adapters.inbound.http.authentication import (
    AuthenticationPorts,
    ReviewerAuthentication,
)
from adapters.inbound.http.authentication import (
    create_router as create_authentication_router,
)
from adapters.inbound.http.health import create_router as create_health_router
from adapters.inbound.http.hospital_approval import (
    create_router as create_hospital_approval_router,
)
from adapters.inbound.http.ledger_proofs import create_router as create_ledger_router
from adapters.inbound.http.policies import create_router as create_policy_router
from adapters.inbound.http.research_authorization import (
    create_router as create_research_authorization_router,
)
from adapters.inbound.http.research_requests import (
    create_router as create_research_router,
)
from adapters.inbound.http.sync_authorization import (
    create_router as create_sync_authorization_router,
)
from adapters.inbound.http.synchronization_requests import (
    create_router as create_synchronization_router,
)
from adapters.outbound.besu_audit_ledger import BesuAuditLedger
from adapters.outbound.credential_file import CredentialFile
from adapters.outbound.in_memory_audit_trail import InMemoryAuditTrail
from adapters.outbound.fixture_policies import load_policies
from adapters.outbound.fixture_patient_grants import FixturePatientGrantDirectory
from adapters.outbound.http_patient_grants import (
    HttpPatientGrantDirectory,
    load_hospital_nodes,
)
from adapters.outbound.in_memory_hospital_applications import SeedError
from adapters.outbound.fixture_reviewer_directory import FixtureReviewerDirectory
from adapters.outbound.in_memory_hospital_applications import (
    InMemoryHospitalApplicationStore,
)
from adapters.outbound.in_memory_research import InMemoryResearchStore
from adapters.outbound.in_memory_sessions import InMemorySessionStore
from adapters.outbound.in_memory_synchronization import InMemorySynchronizationStore
from adapters.outbound.scrypt_password_hasher import ScryptPasswordHasher
from adapters.outbound.simulated_audit_ledger import SimulatedAuditLedger
from application.authentication import CredentialStore, PasswordHasher
from application.get_node_status import NODE_VERSION
from application.ledger import AuditLedgerPort
from application.synchronization import PatientGrantDirectory
from domain.authentication import SignInThrottle
from domain.node_identity import NodeIdentity

# The fictional Governance / Ethics Authority of the demo dataset
# (demo-data/organizations.json). One Governance Node process (ADR-0003).
DEMO_IDENTITY = NodeIdentity(
    node_ref="node-governance", organization_ref="org-governance"
)
# Suggested Governance Node port (ADR-0003); the Federation Service defaults to it.
PORT = 8200
# Where the fictional seed data is read at startup; the repository's demo-data/ by default.
DEMO_DATA_ENV = "GOVERNANCE_NODE_DEMO_DATA"
DEFAULT_DEMO_DATA = Path(__file__).resolve().parents[2] / "demo-data"
# Where patient grants are evaluated (HC-136): `http` (default) asks the Hospital Node
# holding them; `fixture` reads the fictional seed grants instead (MOCKED, opt-in).
GRANTS_ENV = "GOVERNANCE_GRANTS"
HOSPITAL_NODES_ENV = "GOVERNANCE_HOSPITAL_NODES"
DEFAULT_HOSPITAL_NODES = Path(__file__).resolve().parent / "hospital-nodes.demo.json"
# Where decisions are anchored (HC-194, ADR-0007): `simulated` (default) is the MOCKED
# in-memory ledger of HC-191; `besu` is the AuditAnchor contract on a Besu (QBFT) chain,
# at GOVERNANCE_LEDGER_CONTRACT, or deployed anew at startup if that is not set.
LEDGER_ENV = "GOVERNANCE_LEDGER"
LEDGER_RPC_ENV = "GOVERNANCE_LEDGER_RPC_URL"
DEFAULT_LEDGER_RPC = "http://127.0.0.1:8545"
LEDGER_KEY_FILE_ENV = "GOVERNANCE_LEDGER_KEY_FILE"
LEDGER_CONTRACT_ENV = "GOVERNANCE_LEDGER_CONTRACT"
# Who may decide (HC-211, ADR-0010): `off` (default) keeps the declared reviewer_ref;
# `required` serves sign-in and makes each decision need the reviewer's bearer session,
# against the password hashes of GOVERNANCE_CREDENTIALS (auth/.credentials.json).
AUTH_ENV = "GOVERNANCE_AUTH"
CREDENTIALS_ENV = "GOVERNANCE_CREDENTIALS"
DEFAULT_CREDENTIALS = Path(__file__).resolve().parent / "auth" / ".credentials.json"


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def create_app(
    identity: NodeIdentity = DEMO_IDENTITY,
    demo_data: Path = DEFAULT_DEMO_DATA,
    clock: Callable[[], datetime] = _now,
    grants: PatientGrantDirectory | None = None,
    ledger: AuditLedgerPort | None = None,
    credentials: CredentialStore | None = None,
    hasher: PasswordHasher | None = None,
) -> FastAPI:
    """`grants` defaults to the MOCKED fixture grants of `demo_data`, for tests and
    demos; the module-level app chooses from GOVERNANCE_GRANTS, HTTP by default.
    `ledger` defaults to the MOCKED simulated ledger; the module-level app chooses
    from GOVERNANCE_LEDGER, simulated by default. Without `credentials`,
    authentication is off; with them it is required (HC-211)."""
    # HC-131: in memory, seeded from fictional applications; decisions lost on restart.
    applications = InMemoryHospitalApplicationStore.load(demo_data / "governance.json")
    reviewers = FixtureReviewerDirectory.load(demo_data / "people.json")
    # HC-132: in memory, seeded from fictional requests; lost on restart.
    synchronizations = InMemorySynchronizationStore.load(demo_data / "governance.json")
    if grants is None:
        # MOCKED: the fictional seed grants, not the Hospital Nodes' own.
        grants = FixturePatientGrantDirectory.load(demo_data / "access.json")
    # HC-133: in memory, seeded from fictional requests and projects; lost on restart.
    research = InMemoryResearchStore.load(
        demo_data / "governance.json", demo_data / "research.json"
    )
    # HC-135: the governance policy versions, read once from fictional data.
    policies = load_policies(demo_data / "governance.json")
    # HC-134: in memory, seeded from fictional events; runtime events lost on restart.
    audit = InMemoryAuditTrail.load(demo_data / "governance.json")
    if ledger is None:
        # HC-191: MOCKED simulated ledger, in memory, seeded from the fictional proofs;
        # every decision recorded is anchored there. Runtime proofs lost on restart.
        ledger = SimulatedAuditLedger.load(demo_data / "governance.json", audit, clock)
    # HC-211: sessions in memory, lost on restart; sign-in failures throttled per account.
    sessions = InMemorySessionStore() if credentials is not None else None
    auth = ReviewerAuthentication(sessions, clock)
    app = FastAPI(title="Governance Node", version=NODE_VERSION)
    app.include_router(create_health_router(identity, grants.mode, auth.mode))
    if credentials is not None and sessions is not None:
        ports = AuthenticationPorts(
            credentials, hasher or ScryptPasswordHasher(), sessions, SignInThrottle()
        )
        app.include_router(create_authentication_router(ports, reviewers, clock))
    app.include_router(
        create_hospital_approval_router(
            applications, reviewers, policies, audit, clock, ledger, auth
        )
    )
    app.include_router(
        create_synchronization_router(
            synchronizations,
            reviewers,
            grants,
            applications,
            policies,
            audit,
            clock,
            ledger,
            auth,
        )
    )
    app.include_router(
        create_sync_authorization_router(synchronizations, grants, audit, clock)
    )
    app.include_router(
        create_research_router(
            research, reviewers, applications, policies, audit, clock, ledger, auth
        )
    )
    app.include_router(create_research_authorization_router(research, audit, clock))
    app.include_router(create_audit_router(identity, audit))
    app.include_router(create_ledger_router(identity, ledger, audit))
    app.include_router(create_policy_router(policies, clock))
    return app


def grants_from_env(demo_data: Path) -> PatientGrantDirectory:
    """HC-136: the Hospital Nodes' own grants over HTTP unless the MOCKED fixture is
    asked for. Any other value, or an invalid node directory, stops startup."""
    mode = os.environ.get(GRANTS_ENV, "http")
    if mode == "http":
        nodes = Path(os.environ.get(HOSPITAL_NODES_ENV, DEFAULT_HOSPITAL_NODES))
        return HttpPatientGrantDirectory(load_hospital_nodes(nodes))
    if mode == "fixture":
        return FixturePatientGrantDirectory.load(demo_data / "access.json")
    raise SeedError(f"{GRANTS_ENV} must be 'http' or 'fixture', not {mode!r}")


def ledger_from_env() -> AuditLedgerPort | None:
    """HC-194: None for the MOCKED simulated ledger (default), or the Besu ledger.
    Any other value, a missing key file, or a failed deployment stops startup."""
    mode = os.environ.get(LEDGER_ENV, "simulated")
    if mode == "simulated":
        return None
    if mode == "besu":
        key_file = os.environ.get(LEDGER_KEY_FILE_ENV)
        if not key_file:
            raise SeedError(f"{LEDGER_ENV}=besu needs {LEDGER_KEY_FILE_ENV}")
        return BesuAuditLedger.connect(
            os.environ.get(LEDGER_RPC_ENV, DEFAULT_LEDGER_RPC),
            Path(key_file),
            os.environ.get(LEDGER_CONTRACT_ENV) or None,
        )
    raise SeedError(f"{LEDGER_ENV} must be 'simulated' or 'besu', not {mode!r}")


def credentials_from_env(demo_data: Path) -> CredentialStore | None:
    """HC-211: None when authentication is off (default), or the credential file.
    Any other value, or a missing or invalid credential file, stops startup."""
    mode = os.environ.get(AUTH_ENV, "off")
    if mode == "off":
        return None
    if mode == "required":
        path = Path(os.environ.get(CREDENTIALS_ENV, DEFAULT_CREDENTIALS))
        people = FixtureReviewerDirectory.load(demo_data / "people.json")
        return CredentialFile.load(path, people)
    raise SeedError(f"{AUTH_ENV} must be 'off' or 'required', not {mode!r}")


_demo_data = Path(os.environ.get(DEMO_DATA_ENV, DEFAULT_DEMO_DATA))
app = create_app(
    demo_data=_demo_data,
    grants=grants_from_env(_demo_data),
    ledger=ledger_from_env(),
    credentials=credentials_from_env(_demo_data),
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)
