# ADR-0010: Authentication foundation — each runtime authenticates its own users, password sign-in with opaque bearer sessions

## Status

Accepted — 2026-10-11, chosen by the HC-211 assignee during HC-211 ([#164](https://github.com/Medmas07/Hackcure_hackathon/issues/164)); subject to pull-request review. It settles how people authenticate to a runtime at initial depth D2. Role-based access control (HC-212), organization identity (HC-213), and signed federation authorization (HC-214) stay with their own tickets.

## Context

No runtime authenticated anyone. The Governance Node, the Governance / Ethics Authority's boundary, recorded hospital, synchronization, and research decisions under a `reviewer_ref` the caller declared, so anyone who could reach it could decide as `usr-olfa`. HC-210 added deterministic demo personas to the Governance Portal only, in the browser (D1, MOCKED), and the Portal does not call the Node. [ADR-0003](ADR-0003-backend-runtime-strategy.md) left authentication to its own decision, and [OPEN_QUESTIONS](../OPEN_QUESTIONS.md) asked which provider and identity architecture would serve the ecosystem's people and Nodes.

Forces:

- **Federation:** the ecosystem has no central clinical database, and should not get a central user database by accident either. Each organization controls its own people.
- **Clean / Hexagonal Architecture:** credentials, hashing, and sessions stay behind application-owned ports, with no framework or library in Domain or Application.
- **Python 3.12 and FastAPI** (ADR-0003); no new dependency without need.
- **Team operating cost** in a two-day hackathon: no Java or container runtime to run for a login, no paid service.
- **Honesty of status:** fictional demo people, held in memory, are not production identity.

## Decision

1. **Each runtime authenticates the people who act on it, from its own credentials.** There is no central identity provider and no shared user store. The first runtime to do so is the Governance Node, for the people who record decisions there. A Hospital Node would authenticate its own staff the same way, when a ticket asks for it.
2. **Contract:** [`authentication.v1.yaml`](../../contracts/api/auth/authentication.v1.yaml): `POST /v1/auth/sessions` signs in with a person reference and a password, `GET /v1/auth/session` reads the session, `DELETE /v1/auth/session` signs out.
3. **Passwords:** a salted scrypt hash per person, with the standard library's `hashlib.scrypt`. The default cost is n=2^15, r=8, p=3 (32 MiB), one of the OWASP Password Storage settings; each stored hash carries its own cost, so a higher cost can be adopted later without breaking older hashes. Hashes are compared in constant time. Without a stored hash, a verification still runs against a throwaway hash, so timing does not reveal which accounts exist.
4. **Credentials file:** a local JSON file of hashes (`auth/.credentials.json`, gitignored, or `GOVERNANCE_CREDENTIALS`). The `auth/set_password.py` command creates it. Each entry must name staff or a clinician of the demo dataset, and the Node refuses to start on a malformed file.
5. **Sessions:** a random 256-bit opaque bearer token (`secrets.token_urlsafe(32)`), returned once, sent as `Authorization: Bearer`, and kept by the runtime only as its SHA-256 digest. A session lasts 8 hours and ends on sign-out or restart. Responses carrying session data are `Cache-Control: no-store`, and a `401` carries an RFC 6750 `WWW-Authenticate: Bearer` challenge.
6. **Sign-in throttling:** 5 failures in a row lock an account for 15 minutes. Unknown person, wrong password, and locked account all get the same `401 authentication_failed`.
7. **What it protects in the Governance Node:** its three decision routes. With authentication required, a decision without a valid session is `401 authentication_required`, and one whose `reviewer_ref` is not the signed-in person is `403 reviewer_mismatch`. The review rules still decide who may decide: signing in does not make anyone a reviewer. The three decision contracts declare the bearer session as optional (hospital approval 1.2.0, synchronization requests 1.3.0, research requests 1.2.0).
8. **Selection by environment, off by default:** `GOVERNANCE_AUTH=off|required`. Off, the Node behaves as before (declared reviewer) and serves no sign-in routes, so the demo runs without credentials. Required, it needs the credentials file. `GET /health` reports the mode as `authentication`. This follows the opt-in pattern of [ADR-0007](ADR-0007-permissioned-audit-ledger.md).

## Alternatives considered

- **An OpenID Connect provider (Keycloak or similar):** the standard production answer, with MFA, federation, and password reset. Rejected for now because it means a Java or container runtime to operate, and one provider for every organization would centralize identity. It stays the likely upgrade path, ideally one provider per organization, federated. The bearer-token boundary chosen here does not prevent it.
- **Signed stateless tokens (JWT):** they let other services verify a token without asking the issuer, but bring key management and make revocation harder. One runtime checking its own sessions does not need them. Cross-node trust is HC-214's subject.
- **Mutual TLS or API keys:** they identify services, not people. Service-to-service authentication stays OPEN.
- **Argon2id or bcrypt:** OWASP's first choice is Argon2id, but it needs a new native dependency. scrypt is in the standard library and on OWASP's list.
- **Making authentication required by default:** stronger, but every demo of the Node would then need credentials created first. Rejected for D2; the mode is visible in `/health`.

## Consequences

### Positive

- With authentication required, a Governance decision is recorded under the identity of the person who signed in, not one the caller claims.
- No central user store; it fits the federated model.
- No new dependency, no extra process, and everything runs in tests without network or databases.

### Negative

- Off by default: a Node started without `GOVERNANCE_AUTH=required` still trusts a declared reviewer.
- Sessions and failure counts are held in memory, so a restart signs everyone out and unlocks every account. One process only.
- Account lockout lets someone who knows a person reference lock that account for 15 minutes.
- No MFA, password reset, account administration, sign-in audit events, or federation with organizations' identity providers. Credentials belong to fictional demo people; this is not production identity.
- Reads, submissions, and the service-to-service authorization checks remain unauthenticated. The Governance Portal still uses HC-210's demo personas and does not sign in to the Node.

## Follow-up

- HC-212: role-based access control on top of the authenticated person.
- HC-213: hospital organization identity; HC-214: signed federation authorization between Nodes and services.
- HC-215: threat model and security review, including sign-in audit events and lockout abuse.
- Governance Portal sign-in against the Node, once the Portal calls the Node.
- Persistence of sessions and credentials, when persistence is decided.
