"""contracts/api/auth/authentication.v1.yaml (HC-211, ADR-0010).

Sign in with a password for a bearer session, read it, and sign out. With
authentication required, the decision routes call `ReviewerAuthentication`: a decision
needs a bearer session, and its reviewer_ref must be the signed-in person. Off, they
keep HC-131's declared reviewer_ref.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from adapters.inbound.http.problems import OPAQUE_REF, first_error, problem
from application.authentication import (
    CredentialStore,
    PasswordHasher,
    SessionStore,
    authenticate,
    sign_in,
    sign_out,
)
from application.hospital_approval import ReviewerDirectory
from domain.authentication import (
    AuthenticationFailed,
    NotAuthenticated,
    Session,
    SignInThrottle,
)
from domain.hospital_approval import Reviewer

NOTICE = (
    "Sessions are held in memory by the Governance Node and end when it restarts. "
    "Password sign-in for fictional demo people (HC-211, D2): not production identity."
)
REALM = 'Bearer realm="governance-node"'
NO_STORE = {"Cache-Control": "no-store"}


@dataclass(frozen=True)
class AuthenticationPorts:
    credentials: CredentialStore
    hasher: PasswordHasher
    sessions: SessionStore
    throttle: SignInThrottle


class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_ref: Annotated[str, Field(pattern=OPAQUE_REF.pattern)]
    # Bounded: each sign-in costs a scrypt derivation.
    password: Annotated[str, Field(min_length=1, max_length=1024)]


def unauthenticated(detail: str, invalid_token: bool) -> JSONResponse:
    response = problem(
        401, "Authentication required", "authentication_required", detail
    )
    response.headers["WWW-Authenticate"] = REALM + (
        ', error="invalid_token"' if invalid_token else ""
    )
    return response


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise NotAuthenticated("The Authorization header is not a bearer token.")
    return token.strip()


def _session(
    request: Request, sessions: SessionStore, clock: Callable[[], datetime]
) -> Session | JSONResponse:
    try:
        token = _bearer_token(request)
        if token is None:
            return unauthenticated("A bearer session is required.", invalid_token=False)
        return authenticate(token, sessions, clock)
    except NotAuthenticated as error:
        return unauthenticated(str(error), invalid_token=True)


class ReviewerAuthentication:
    """Off (`sessions` None): the reviewer is declared. Required: it is signed in."""

    def __init__(
        self, sessions: SessionStore | None, clock: Callable[[], datetime]
    ) -> None:
        self._sessions = sessions
        self._clock = clock

    @property
    def mode(self) -> str:
        return "off" if self._sessions is None else "required"

    def caller(self, request: Request) -> str | None | JSONResponse:
        """The signed-in person, None when off, or the 401 to answer."""
        if self._sessions is None:
            return None
        session = _session(request, self._sessions, self._clock)
        return session if isinstance(session, JSONResponse) else session.person_ref

    @staticmethod
    def refuse(caller: str | None, reviewer_ref: str) -> JSONResponse | None:
        if caller is None or caller == reviewer_ref:
            return None
        return problem(
            403,
            "Reviewer mismatch",
            "reviewer_mismatch",
            f"reviewer_ref {reviewer_ref} is not the signed-in person {caller}.",
        )


def _person(session: Session, person: Reviewer) -> dict:
    return {
        "person_ref": session.person_ref,
        "role": person.role,
        "organization_ref": person.organization_ref,
        "issued_at": session.issued_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "notice": NOTICE,
    }


def create_router(
    ports: AuthenticationPorts,
    people: ReviewerDirectory,
    clock: Callable[[], datetime],
) -> APIRouter:
    router = APIRouter(tags=["authentication"])

    @router.post("/v1/auth/sessions")
    async def create_session(request: Request) -> JSONResponse:
        try:
            body = SignInRequest.model_validate_json(await request.body())
        except ValidationError as error:
            return problem(
                400, "Invalid request", "invalid_request", first_error(error)
            )
        try:
            signed_in = await run_in_threadpool(
                sign_in,
                body.person_ref,
                body.password,
                ports.credentials,
                ports.hasher,
                people,
                ports.sessions,
                ports.throttle,
                clock,
            )
        except AuthenticationFailed:
            return problem(
                401,
                "Authentication failed",
                "authentication_failed",
                "Sign-in refused: unknown person, wrong password, or too many "
                "failed attempts.",
            )
        return JSONResponse(
            {
                "session_token": signed_in.token,
                "token_type": "Bearer",
                **_person(signed_in.session, signed_in.person),
            },
            status_code=201,
            headers=NO_STORE,
        )

    @router.get("/v1/auth/session")
    def get_session(request: Request) -> JSONResponse:
        session = _session(request, ports.sessions, clock)
        if isinstance(session, JSONResponse):
            return session
        person = people.reviewer(session.person_ref)
        if person is None:
            return unauthenticated(
                "The signed-in person is unknown.", invalid_token=True
            )
        return JSONResponse(_person(session, person), headers=NO_STORE)

    @router.delete("/v1/auth/session", status_code=204)
    def delete_session(request: Request) -> Response:
        try:
            token = _bearer_token(request)
            if token is None:
                return unauthenticated(
                    "A bearer session is required.", invalid_token=False
                )
            sign_out(token, ports.sessions, clock)
        except NotAuthenticated as error:
            return unauthenticated(str(error), invalid_token=True)
        return Response(status_code=204)

    return router
