# ADR-0011: Role-based access control — a fixed role matrix per runtime, checked on every protected route

## Status

Accepted — 2026-10-11, chosen by the HC-212 assignee during HC-212 ([#165](https://github.com/Medmas07/Hackcure_hackathon/issues/165)); subject to pull-request review. It settles what an authenticated person may do at a runtime, at initial depth D2. Organization identity (HC-213) and signed federation authorization (HC-214) stay with their own tickets.

## Context

[ADR-0010](ADR-0010-authentication-foundation.md) (HC-211) made the Governance Node authenticate the people who record decisions, opt-in with `GOVERNANCE_AUTH=required`. A session only said who was calling. Every other route stayed open: anyone who could reach the Node could read every hospital application, synchronization and research request, the audit trail, and the ledger proofs, and could submit requests under any declared `submitted_by_ref`. The only "who may do what" rule was in the domain: a decision needs a `governance_reviewer`.

The demo dataset ([`demo-data/people.json`](../../demo-data/people.json)) gives each person one role: `governance_reviewer`, `hospital_manager`, `researcher`, `physician`, `nurse`, and patients and relatives. HC-210's Governance Portal already shows browser-side scopes per role (`governance:review`, `governance:audit`, …; D1, MOCKED), and the product vision places Identity / RBAC in each Node.

Forces:

- **Federation:** each runtime controls who may act on it; no central permission service.
- **Clean / Hexagonal Architecture:** the role matrix is a domain rule; HTTP only asks.
- **Honesty of status:** fictional roles held in a demo file are not a validated access policy.
- **Two-day hackathon:** no policy engine, no administration UI.

## Decision

1. **A fixed role-to-permission matrix in each runtime's domain, deny by default.** In the Governance Node, `domain/access_control.py`:

   | Role | Permissions |
   |---|---|
   | `governance_reviewer` | `governance:review` (read applications and requests, decide), `governance:audit` (read the audit trail and ledger proofs) |
   | `hospital_manager` | `synchronization:request` |
   | `physician` | `synchronization:request` |
   | `researcher` | `research:request` |
   | any other role (`nurse`, patients, relatives, unknown) | none |

   Permission names reuse HC-210's `domain:action` form. No role both requests and reviews.
2. **Every protected route names one permission, and checks it on every call** (`application/access_control.py`'s `authorize`): a valid session (`401 authentication_required` otherwise), then the person's role from the people directory, then the matrix (`403 permission_denied`). The check runs before anything is looked up, so a role without the permission cannot learn which records exist.
3. **The domain's review rules read the same matrix.** "Only a governance reviewer may decide" becomes "only a role that grants `governance:review`", in authentication-off mode too, so there is one source of truth.
4. **A declared actor must be the caller.** As HC-211 did for `reviewer_ref`, a submission's `submitted_by_ref` must be the signed-in person (`403 submitter_mismatch`).
5. **What stays open:** `GET /health`, the published governance policies (the rules every decision cites), sign-in, and the two service authorization checks the Federation and Research Services call. Those identify services, not people: HC-214.
6. **Same switch as HC-211.** Enforcement applies only with `GOVERNANCE_AUTH=required`. Off, the default, nothing is checked, as before.
7. **The session shows the grants.** `authentication.v1.yaml` 1.1.0 adds `permissions` to the sign-in and session responses, for display; the routes never trust it from the client.

## Alternatives considered

- **Roles and permissions in a data file or policy engine (OPA, Casbin):** editable without code, but a policy engine is a new runtime and dependency, and an editable file raises "who approves a change", the same question HC-135's policy versions left OPEN. Rejected for D2; the matrix is small and reviewed in pull requests.
- **Scopes in the token (JWT claims):** the token would carry what the holder may do and could go stale. Sessions are opaque and checked by the runtime that issued them (ADR-0010), so the runtime reads the role at each call.
- **Checking only decisions, as HC-211 did:** leaves every read of governance records open. Rejected: the ticket's subject is who may do what.
- **Multiple roles per person:** the demo data gives each person one role; a list can be added later without changing the routes.

## Consequences

### Positive

- With authentication required, governance records, the audit trail, and ledger proofs are served only to governance reviewers, and requests are submitted only by roles that may ask, under their own name.
- One matrix decides both the HTTP check and the domain's review rule.
- No new dependency or process; testable without network or databases.

### Negative

- Off by default, like HC-211: a Node started without `GOVERNANCE_AUTH=required` checks nothing.
- Role-level only: a hospital manager may submit a synchronization request for any organization, and a reviewer reads every organization's records. Restricting a person to their own organization is HC-213.
- The matrix is fixed fictional demo policy, changed only by code; not a validated access policy.
- Permission denials are not audited (HC-215 covers sign-in and denial audit).
- The service authorization checks stay unauthenticated (HC-214).

## Follow-up

- HC-213: organization identity, so a person acts only for their organization.
- HC-214: service authentication for the authorization checks.
- HC-215: audit of denials and sign-ins, in the threat model.
- The Governance Portal using the Node's session and `permissions` in place of HC-210's browser-side scopes.
- Each Hospital Node's own role matrix, when it authenticates its staff.
