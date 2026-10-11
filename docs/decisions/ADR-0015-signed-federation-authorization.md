# ADR-0015: Signed federation authorization — the Governance Node signs each authorized exchange with Ed25519, and the Hospital Node verifies it on its own

## Status

Accepted — 2026-10-11, chosen by the HC-214 assignee during HC-214 ([#167](https://github.com/Medmas07/Hackcure_hackathon/issues/167)); subject to pull-request review. It settles how a Hospital Node verifies, by itself, that the Governance / Ethics Authority authorized a query under a synchronization decision. Authentication between services (who may call whom) stays OPEN.

## Context

Under a synchronization decision, the Federation Service asks the Governance Node whether the decision authorizes the exact exchange ([`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml), HC-144), then asks only the organizations Governance names. The [Hospital Node federation contract](../../contracts/federation/hospital-node-federation.v1.yaml) requires each node to enforce the authorization itself and not rely on the Federation Service's check, but left how it verifies a decision OPEN. The Hospital Node runtime stood in for it with a MOCKED verifier: fictional decisions read from `demo-data/governance.json` at startup (HC-114). A decision the Governance Node recorded at runtime, such as demo step 20's approval of `sync-001`, was therefore unknown to the node and denied, and nothing tied the node's answer to the Authority's actual decision. [ADR-0010](ADR-0010-authentication-foundation.md) and [ADR-0014](ADR-0014-organization-identity.md) left this to HC-214.

Forces:

- **Federation:** the Hospital Node keeps control of its data and decides on its own; no central service reaches into it, and it should not depend on reaching the Governance Node for every query.
- **Governance decides; Federation enforces:** the Federation Service must not be able to create or widen an authorization. A node must be able to tell that the Authority, not the service carrying the query, said yes.
- **Consent still holds:** the Governance Node re-verifies the patient grant on every check (HC-136); a revoked grant must stop the exchange quickly.
- **Clean / Hexagonal Architecture:** what is attested and when it covers a query are domain rules; signing and verifying are adapters behind application-owned ports.
- **Python 3.12 and FastAPI** (ADR-0003); a two-day hackathon: no PKI, HSM, or identity provider to run.
- **Honesty of status:** a key pair on a developer's disk is not production key management.

## Decision

1. **The Governance Node signs what it authorizes.** When a synchronization check is `authorized`, the answer carries `signed_authorization` (sync-authorization-check 1.2.0): a compact JWS (RFC 7515) with `alg: EdDSA` (RFC 8037, Ed25519). It attests the issuer (the Authority's organization), the decision (`sub`), the target organizations (`aud`), and the exact exchange asked: requester organization, actor, patient, scope as asked (never the wider approved scope), and purpose. The rules are in `domain/federation_authorization.py`; signing is the `AuthorizationSigner` port, implemented by `adapters/outbound/ed25519_authorization_signer.py`.
2. **Short-lived.** A signed authorization expires at the earlier of the decision's `valid_until` and five minutes after the check. The Federation Service checks with Governance before each query, so a decision that expires or a patient grant withdrawn at its Hospital Node stops the exchange within five minutes, without the node calling Governance.
3. **The Federation Service passes it on unchanged.** It takes `signed_authorization` from the check and sends it with the query to each target node (hospital-node-federation 1.1.0, optional field). It never creates, alters, or widens it, and it does not verify it.
4. **The Hospital Node verifies it on its own.** Configured with the Governance Node's public key (`governance_public_key`) and organization (`governance_organization_ref`), the node accepts a synchronization-decision query only if: the header is exactly `alg EdDSA`, the trusted key's RFC 7638 thumbprint as `kid`, and `typ governance-authorization+jwt`; the signature verifies; the claims are exactly the contract's; the issuer is the trusted Authority; its own organization is in the audience; decision, requester, actor, patient, and purpose match the query; the query's scope is within the attested one; and the time is between issue (60 seconds of clock skew tolerated) and expiry. Anything else is `403 authorization_denied`, audited as denied. The rules are in `domain/signed_authorization.py` and `application/authorization_verifier.py` (`SignedDecisionVerifier`); signature checking is the `SignedAuthorizationReader` port, implemented by `adapters/outbound/ed25519_authorization_reader.py`. Patient access grants are unaffected: the node holding a grant checks it in its own store.
5. **Ed25519 with the `cryptography` package**, in the two runtimes' outbound adapters only. The standard library has no asymmetric signatures.
6. **Keys:** `python -m auth.create_signing_key` in the Governance Node writes a new private key (`auth/.signing-key.pem`, gitignored, owner-readable where the platform honours file modes) and its public key next to it. The public key is given to each Hospital Node out of band; it is configuration, not fetched over the network.
7. **Opt-in, like ADR-0007, ADR-0010, and ADR-0011.** `GOVERNANCE_FEDERATION_SIGNING=off|ed25519` (off by default; `null` token) and `GOVERNANCE_SIGNING_KEY`; a Hospital Node without `governance_public_key` keeps the MOCKED fixture decisions. Each `/health` reports its mode (`federation_signing`, `synchronization_decisions`). A Hospital Node configured to verify denies every synchronization-decision query without a valid signed authorization, including when the Governance Node does not sign.

## Alternatives considered

- **The Hospital Node asks the Governance Node online for each query:** simple and always current, but it makes each hospital depend on reaching Governance for every query, and still needs service authentication to trust the answer. Signed, short-lived statements let the node decide alone. Rejected.
- **Shared-secret HMAC (HS256):** standard library only, but every node holding the secret could forge authorizations for every other node. Rejected; signatures must be verifiable without the ability to sign.
- **Long-lived tokens valid until the decision ends:** fewer checks, but a revoked patient grant would keep authorizing exchanges for days. Rejected for five minutes.
- **A JWT library (PyJWT, joserfc):** convenient, but a second dependency and its algorithm negotiation; the token here has one fixed header and claim set, checked strictly. Rejected.
- **Publishing the key at a Governance endpoint (JWKS):** easier rotation, but fetching it over unauthenticated HTTP would let whoever answers choose the trusted key. Deferred until transport and service identity are decided.
- **Mutual TLS between services:** authenticates who is calling, not what the Authority decided; complementary, and still OPEN.

## Consequences

### Positive

- A Hospital Node can verify, alone, that the Governance / Ethics Authority authorized exactly this exchange, for itself, now. Decisions recorded at runtime work end to end; the Federation Service cannot widen them.
- Federation stays federated: no node calls Governance per query, and no clinical data reaches Governance or the token (opaque references only).
- One dependency, two small adapters, testable without network or databases.

### Negative

- Off by default; with signing off, or a node without a public key, nothing changes.
- A signed authorization is a bearer credential for five minutes: whoever obtains it can replay the same exchange. No replay cache (the Federation Service's retries reuse it), and no revocation before expiry.
- Key management is a file on disk: no rotation beyond replacing the key and redistributing the public key, one key at a time, no HSM. Trust in the public key rests on how it was distributed.
- Services are still not authenticated to each other, and transport is plain HTTP in the demo: who may ask the Governance check, and the Federation Service's own identity, remain OPEN. Research authorization checks (HC-133) are not signed. The simulated nodes (HC-141) ignore the token.
- The organizations and decisions remain fictional demo data; this is not production security and not VALIDATED by a security review (HC-215).

## Follow-up

- HC-215: threat model and security review, including token replay, key custody, and transport security.
- Service authentication (mutual TLS or signed requests) and key rotation with more than one trusted key.
- Signing research authorizations for Compute-to-Data execution, if a ticket asks for node-side verification there.
