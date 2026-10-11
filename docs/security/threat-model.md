# Security audit and threat model (HC-215)

**Status:** IMPLEMENTED (D4) as a repository-inspection audit and threat model, dated 2026-10-11, of `main` at `a12335b` plus the HC-215 changes. It is **not** an independent security review, a penetration test, or a compliance assessment, and it makes **no production-security claim**. Nothing here is VALIDATED by a third party. Every data set in the repository is fictional ([ADR-0005](../decisions/ADR-0005-canonical-demo-data.md)).

HC-215 also adds one control the earlier tickets left to it: the Governance Node now **audits sign-ins and access denials** ([section 6](#6-control-added-by-hc-215-security-audit-events)). Every other finding below is recorded, not fixed, and is tracked by a follow-up issue ([section 8](#8-follow-up-issues)).

## 1. Scope and method

In scope: the runtimes in this repository and the contracts between them.

| Runtime | Path | Local port ([ADR-0003](../decisions/ADR-0003-backend-runtime-strategy.md)) |
|---|---|---|
| Hospital Node (one process per hospital) | [`instances/hospital-node/`](../../instances/hospital-node/README.md) | 8101–8103 |
| Governance Node | [`instances/governance-node/`](../../instances/governance-node/README.md) | 8200 |
| Federation Service | [`services/federation/`](../../services/federation/README.md) | 8300 |
| Research Service | [`services/research/`](../../services/research/README.md) | 8400 |
| Notification Service | [`services/notifications/`](../../services/notifications/README.md) | 8500 |
| AI Services | [`services/ai/`](../../services/ai/README.md) | 8600 |
| SciAgents integration | [`integrations/sciagents/`](../../integrations/sciagents/README.md) | 8800 |
| Web portals, Patient App | [`apps/`](../../apps/) | 5173–5175 |

Method: we read the code of every inbound HTTP route and the authentication, authorization, signing, audit, and ledger code. We also read the contracts, ADR-0003, ADR-0007, ADR-0010, ADR-0011, ADR-0014, and ADR-0015, and the component READMEs. We searched for committed secrets, CORS and bind settings, browser storage, and HTML injection sinks. The threats are organized by STRIDE at each trust boundary. Severity assumes a **production-like deployment** where the services can reach each other over a network. In the demo, every runtime listens on `127.0.0.1` and that loopback binding is the main control. Out of scope: the external SciAgents system, a running Besu network, mobile platform security, physical security, and IoT.

## 2. Assets

| Asset | Owner | Where it lives today |
|---|---|---|
| Clinical source data (records, labs, medications) | Each Hospital Node | MOCKED fixtures, in memory |
| Patient access grants (consent) | The Hospital Node holding them | In memory |
| Hospital Node audit trail (names patients and requesters) | Each Hospital Node | In memory |
| Governance decisions, requests, and audit trail | Governance Node | In memory, seeded from fixtures |
| Federation signing private key (Ed25519) | Governance Node | `auth/.signing-key.pem`, gitignored |
| Password hashes (scrypt) and bearer sessions | Governance Node | `auth/.credentials.json` (gitignored); sessions as SHA-256 digests in memory |
| Ledger anchoring key | Governance Node | `ledger/.chain/anchor.key`, gitignored |
| Controlled research results | Research Service | In memory |
| Notification texts (some with clinical content) | Notification Service | In memory |
| LLM provider credentials | AI Services | Environment, `.env` gitignored |

## 3. Trust boundaries and actors

```text
 Browser / Patient App ──► Portals (static SPA) ──► Governance Node (8200)
                                         │                 ▲ sync / research checks
                                         ▼                 │
 Researcher ─► Research Service (8400) ─────► Hospital Node A/B (8101/8102) ◄── Federation Service (8300)
                                                    │ (warning text only, opt-in)
                                                    ▼
                                             AI Services (8600) ─► Claude / Ollama
```

- **TB1 — user to runtime:** people reach the Governance Node, Notification Service, and SciAgents integration.
- **TB2 — service to service:** Federation → Governance check → Hospital Node; Research → Governance check → Hospital Node; Governance → Hospital Node (grant re-verification, HC-136); Hospital Node → AI Services.
- **TB3 — ecosystem to third party:** AI Services → LLM provider; SciAgents integration → external SciAgents.
- **TB4 — operator to host:** key files, credentials files, configuration.

Actors considered: an **outsider** with network reach to a runtime; a **signed-in insider** acting beyond their role; a **malicious or compromised node or service** inside the federation; a **curious operator** with file access.

## 4. Threats by boundary (STRIDE)

The status labels follow [the shared vocabulary](../README.md#status-vocabulary). "Opt-in" means off by default.

| ID | STRIDE | Boundary | Threat | Current control | Residual |
|---|---|---|---|---|---|
| T1 | S | TB1 | Someone acts as a governance reviewer | HC-211 password + bearer session, HC-212 roles, HC-213 organization: IMPLEMENTED, opt-in (`GOVERNANCE_AUTH=required`) | Off by default: declared `reviewer_ref` trusted (F-11). No MFA, no IdP |
| T2 | S | TB1 | Password guessing | scrypt, one `401` for all failures, 5 failures lock for 15 min: IMPLEMENTED | Lockout can be abused to deny service (F-08) |
| T3 | S | TB2 | A caller impersonates the Federation Service at the Governance sync check and obtains a signed authorization | Exact-match check, 5-minute token: IMPLEMENTED | Check callers unauthenticated (F-02) |
| T4 | S/T | TB2 | Forged or widened authorization reaches a Hospital Node | Ed25519 JWS verified on the node, strict header/claims/scope/time: IMPLEMENTED, opt-in (HC-214) | Without `governance_public_key`, MOCKED fixture decisions; research envelopes unsigned (F-03) |
| T5 | S | TB2 | A rogue node registers with the Federation Service and injects fabricated records | Discovery identity check (misrouting only): IMPLEMENTED | Registry writes unauthenticated, approval refs unverified (F-04) |
| T6 | T | TB2 | Anyone creates or revokes a patient's consent grant | None: grant API unauthenticated | F-01 |
| T7 | T | TB4 | Audit events altered after the fact | Append-only in-memory trail; decisions anchored as hashed minimized payloads in a ledger (simulated MOCKED; Besu opt-in) | Not durable; single local validator gives no independent assurance |
| T8 | R | TB1 | A person denies a sign-in or a refused action | **HC-215:** `signed_in`, `sign_in_refused`, `access_denied` audit events: IMPLEMENTED, with authentication required | `401`s and unknown-person sign-ins deliberately not recorded (bounded trail); trail not durable |
| T9 | R | TB2 | A node or service denies an exchange | Governance records each check before answering; Hospital Node records each query answered or refused: IMPLEMENTED | Callers' identities are declared, not authenticated |
| T10 | I | TB2 | Network observer reads clinical payloads or bearer tokens | Loopback binding in the demo | Plain HTTP everywhere (F-09) |
| T11 | I | TB1/TB2 | Anyone reads a Hospital Node's audit trail or a recipient's notifications | Loopback binding | Unauthenticated readers (F-05, F-06) |
| T12 | I | TB3 | Clinical text leaves the hospital boundary to an LLM provider | Explanations send warning content only, never a patient reference; off by default (HC-164) | Clinical extraction sends source text to the configured provider; hosting decision OPEN (F-14) |
| T13 | I | TB4 | Private keys or credentials committed | `.gitignore` entries; `git ls-files` shows only `.env.example` files with no values that are secrets | Key custody is a file on disk (F-07) |
| T14 | I | Ledger | Clinical data placed on-chain | `ProofPayload` limited to six minimized fields; tests forbid patient, actor, purpose, rationale, scope: IMPLEMENTED | None found |
| T15 | I | Research | Re-identification through research output | One preinstalled aggregate, disclosure threshold, output validation, sandboxed child process: IMPLEMENTED (D3/D4) | Not container-grade; Windows reports `parent_enforced` |
| T16 | D | All | Memory exhaustion by unbounded in-memory stores | Request bodies bounded by contract; unknown sign-in refs not tracked | Stores grow without retention (F-10) |
| T17 | D | TB1 | Reviewer locked out by an attacker | Lockout now visible in the audit trail (HC-215) | F-08 |
| T18 | E | TB1 | A signed-in person acts for another person or organization | `reviewer_mismatch`, `submitter_mismatch`, `organization_mismatch` (`403`), now audited | Matrix is fictional demo policy |
| T19 | E | TB2 | A request to a node runs arbitrary code | Only the preinstalled aggregate runs; submitted code is never executed: IMPLEMENTED | None found at D4 |
| T20 | E | TB2 | SSRF through node registration | `follow_redirects=False`, 2 s timeout | Any URL accepted (F-04) |

## 5. Findings

Severity is for a production-like deployment. In the demo, every runtime listens on loopback only when started as documented: `python main.py` for the Hospital and Governance Nodes, and `uvicorn` with no `--host` for the others. `fastapi run` and `--host 0.0.0.0` listen on every interface and remove that control.

| ID | Severity | Finding | Evidence | Proposed remedy |
|---|---|---|---|---|
| F-01 | Critical | The Hospital Node's access-grant API is unauthenticated. Anyone who can reach a node can create a grant to themselves for any patient, then read that patient's history through `POST /v1/federation/queries`, or revoke grants. | [`hospital-node/README.md`](../../instances/hospital-node/README.md) "Callers are not authenticated"; `adapters/inbound/http/access_grants.py` | Authenticate grant callers (patient or delegate identity via the Patient App), and authenticate services (F-09) |
| F-02 | High | The Governance sync-authorization check is unauthenticated. With signing on, anyone who knows an authorized exchange's parameters (opaque but guessable references such as `dec-sync-001`) receives a five-minute signed bearer token and can present it directly to the target node. | `adapters/inbound/http/sync_authorization.py`; [ADR-0015](../decisions/ADR-0015-signed-federation-authorization.md) "Negative" | Authenticate the Federation Service (mTLS or signed requests); bind the token to the caller's key; add a `jti` replay cache on nodes |
| F-03 | High | Research authorization envelopes are neither signed nor authenticated. Anyone who can reach a Hospital Node can send a crafted envelope and run the installed aggregate. | [`CURRENT_STATUS.md`](../CURRENT_STATUS.md) HC-183/HC-186; [ADR-0015](../decisions/ADR-0015-signed-federation-authorization.md) follow-up | Sign research authorizations as HC-214 does for synchronization |
| F-04 | High | Federation registry writes are unauthenticated and their Governance approval references are not verified. A rogue entry can feed fabricated records into federated timelines, and arbitrary node URLs let the service send HTTP requests to internal addresses (SSRF). | [`services/federation/README.md`](../../services/federation/README.md) | Authenticate writes, verify the approval with the Governance Node (`getHospitalApproval`), restrict node URLs to an allowlist |
| F-05 | Medium | The Notification Service reads (`/v1/recipients/{ref}/notifications`, clinician alerts and their stream) and push registration are unauthenticated. CORS allows any origin. Notification texts can carry clinical content (a lab result for a named patient in the contract examples). `NotificationSettings` defaults to `0.0.0.0`, but no runner uses that value today. | `services/notifications/main.py`; `infrastructure/config.py`; [`notification-event.v1.yaml`](../../contracts/events/notification-event.v1.yaml) | Authenticate recipients; restrict CORS to the portals' origins; default host `127.0.0.1` |
| F-06 | Medium | Hospital Node audit readers are unauthenticated, and its trail names patients and requesters. | [`hospital-node/README.md`](../../instances/hospital-node/README.md) audit section | Authenticate readers (hospital staff identity, ADR-0010 per runtime) |
| F-07 | Medium | A signed authorization can be replayed until it expires (at most 5 minutes). There is no early revocation, only one trusted key, and the private key is a file on disk. | [ADR-0015](../decisions/ADR-0015-signed-federation-authorization.md) | `jti` replay cache; several trusted keys by `kid`; key custody in an HSM or KMS |
| F-08 | Medium | Lockout abuse: person references are not secret (they appear in decisions and audit events), so anyone can lock a reviewer out for 15 minutes, repeatedly. Since HC-215 each lockout is audited as `account_locked`. | `domain/authentication.py` | Per-client throttling, MFA or IdP sign-in, alerting on `account_locked` |
| F-09 | Medium | All service-to-service and user traffic is plain HTTP, and services do not authenticate each other. | [`architecture.md`](../architecture.md); [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) | TLS everywhere, mTLS between services (with the deployment tickets) |
| F-10 | Medium | Every store is in memory without retention, so request floods can exhaust memory. A signed-in person can add `access_denied` events without bound (attributed to them). | All `in_memory_*` adapters | Persistence with retention, rate limits at the edge |
| F-11 | Low | Governance authentication is off by default. Off, the declared reviewer and submitter are trusted. `/health` reports the mode. | `main.py`, `GOVERNANCE_AUTH` | Make `required` the default once the portals sign in |
| F-12 | Low | The Governance Portal's D1 authentication is MOCKED in the browser, and the portal does not call the Node. | [`CURRENT_STATUS.md`](../CURRENT_STATUS.md) | Portal sign-in against `authentication.v1.yaml` |
| F-13 | Low | Every FastAPI runtime serves `/docs` and `/openapi.json`. | No `docs_url` override in any `main.py` | Disable outside development |
| F-14 | Info | AI clinical extraction sends source text to the configured LLM provider. Whether clinical text may leave the hospital boundary is OPEN. | [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md); [`services/ai/README.md`](../../services/ai/README.md) | Decide hosting (in-hospital model or a data-processing agreement) before real data |

Checks that found **no issue**:

- No secret, credential, private key, or populated environment file is tracked. The only files tracked are `.env.example` files, which hold model names and localhost URLs.
- No raw clinical data goes into the ledger payload or the governance audit event schema. Both are enforced in domain code and tests.
- Session tokens are stored only as SHA-256 digests, and password verification spends the same time for unknown accounts.
- Signed-authorization verification fixes the algorithm (`EdDSA`) and pins `kid` to the trusted key's thumbprint, so the algorithm cannot be switched and the key cannot be substituted.
- Outbound HTTP clients in the Federation Service do not follow redirects and use 2 s timeouts.
- No web portal uses `localStorage`, `sessionStorage`, or `dangerouslySetInnerHTML`.
- No route executes submitted code.

## 6. Control added by HC-215: security audit events

ADR-0010, ADR-0011, and ADR-0014 left the auditing of sign-ins and denials to HC-215. With `GOVERNANCE_AUTH=required`, the Governance Node now records the following in its own audit trail ([`governance-audit-events.v1.yaml`](../../contracts/api/governance/governance-audit-events.v1.yaml) 1.2.0, domain `security`):

| Action | When | Subject | Reason |
|---|---|---|---|
| `signed_in` | A session is issued (recorded before the token is returned) | `person` | — |
| `sign_in_refused` | A known account's password is wrong, while it is not locked | `person` | `invalid_credentials`, or `account_locked` for the failure that locks it |
| `access_denied` | A signed-in person gets a `403` on a protected route | `permission` (the route's permission) | `permission_denied`, `reviewer_mismatch`, `submitter_mismatch`, `organization_mismatch` |

Design choices:

- **Minimized:** an event never carries a password, a token, a header, or the request's content. It names the actor, the subject reference, the reason code, and the organizations (the Authority, then the person's own).
- **Bounded:** refusals for an unknown person, attempts on a locked account, and `401`s without a valid session are **not** recorded. Recording them would let anyone grow the trail without limit. The lockout therefore caps the recorded refusals at five per known account per 15 minutes.
- **Off means off:** with authentication off, nothing in the security domain is recorded.
- **Clean architecture:** the event rules are in `domain/audit.py`. Recording happens in the `sign_in` and `authorize` use cases and in `record_denial` (`application/`). The HTTP adapter only reports which permission and which mismatch applied.

Tests: domain rules (`tests/test_audit.py`), use cases with test doubles (`tests/test_authentication_use_cases.py`, `tests/test_access_control.py`), and HTTP against the contract, including the contract's `security` example reproduced exactly (`tests/test_security_audit_http.py`).

## 7. Demo validation

From `instances/governance-node/` with a credentials file created by `python -m auth.set_password` (fictional people only):

```sh
GOVERNANCE_AUTH=required python main.py
# a wrong password, then a sign-in
curl -s -X POST localhost:8200/v1/auth/sessions -H 'content-type: application/json' \
  -d '{"person_ref":"usr-olfa","password":"wrong"}'
TOKEN=$(curl -s -X POST localhost:8200/v1/auth/sessions -H 'content-type: application/json' \
  -d '{"person_ref":"usr-olfa","password":"<her password>"}' | python -c 'import json,sys;print(json.load(sys.stdin)["session_token"])')
curl -s 'localhost:8200/v1/audit/events?domain=security' -H "Authorization: Bearer $TOKEN"
```

The answer lists `signed_in` and `sign_in_refused` (`invalid_credentials`) for `usr-olfa`, with no password or token in either event. Signing in as a researcher and reading the trail adds an `access_denied` event (`governance:audit`, `permission_denied`). The response's `notice` and `durable: false` show that the trail is in memory and is not production audit.

## 8. Follow-up issues

Each is in the Backlog of Milestone 6 under the Security & Audit epic (#19); none is implemented.

1. [#305](https://github.com/Medmas07/Hackcure_hackathon/issues/305) Authenticate Hospital Node grant, audit, and research-execution callers (F-01, F-03, F-06).
2. [#306](https://github.com/Medmas07/Hackcure_hackathon/issues/306) Service authentication between runtimes (mTLS or signed requests), and TLS everywhere (F-02, F-09).
3. [#307](https://github.com/Medmas07/Hackcure_hackathon/issues/307) Sign research authorizations, and add a node-side `jti` replay cache for signed authorizations (F-03, F-07).
4. [#308](https://github.com/Medmas07/Hackcure_hackathon/issues/308) Authenticated, Governance-verified Federation registry writes with a URL allowlist (F-04).
5. [#309](https://github.com/Medmas07/Hackcure_hackathon/issues/309) Notification Service recipient authentication, CORS restricted to known origins, and a loopback default host (F-05).
6. [#310](https://github.com/Medmas07/Hackcure_hackathon/issues/310) Sign-in hardening: per-client throttling, MFA or OIDC, alerting on `account_locked` (F-08).
7. [#311](https://github.com/Medmas07/Hackcure_hackathon/issues/311) Durable audit storage with retention (F-10; [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md)).
