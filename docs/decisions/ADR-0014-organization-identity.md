# ADR-0014: Organization identity — a person acts only for their own, recognized organization

## Status

Accepted — 2026-10-11, chosen by the HC-213 assignee during HC-213 ([#166](https://github.com/Medmas07/Hackcure_hackathon/issues/166)); subject to pull-request review. It settles which organization an authenticated person acts for at the Governance Node. Signed federation authorization between Nodes and services (HC-214) stays with its own ticket.

## Context

[ADR-0010](ADR-0010-authentication-foundation.md) (HC-211) made the Governance Node authenticate people, and [ADR-0011](ADR-0011-role-based-access-control.md) (HC-212) checked their role on every protected route, both opt-in with `GOVERNANCE_AUTH=required`. ADR-0011 left two gaps it named as HC-213's subject:

- A hospital manager or physician could submit a synchronization request for any `requester_organization_ref`, and a researcher a research request for any `research_organization_ref`. The Node verified the person, not the institution they claimed to speak for.
- A role was trusted wherever it was held. Nothing stopped a `governance_reviewer` recorded at a hospital, or at the company running the platform, from reviewing; only the conflict-of-interest rule (no decision on one's own organization) applied. The product vision requires the company platform not to be the Governance / Ethics Authority.

The product vision lists "institution identity" among the Governance Node's responsibilities and asks it to verify the requesting institution. The demo dataset gives every staff member and clinician one organization (`demo-data/people.json`), and every organization a type (`demo-data/organizations.json`): `hospital`, `private_practice`, `governance_authority`, `platform_operator`, `research_institution`.

Forces:

- **Federation:** the Authority knows which institutions it governs; it does not own their staff directories. Each Hospital Node keeps its own identity (HC-112).
- **Clean / Hexagonal Architecture:** the affiliation rules are domain rules; the directory of organizations is a port.
- **Honesty of status:** fictional organizations and affiliations read from a demo file are not a verified institution registry.
- **Two-day hackathon:** no identity federation, certificates, or administration UI.

## Decision

1. **The Governance Node keeps a directory of the organizations it knows, with their type**, behind an application `OrganizationDirectory` port. At D3 the adapter reads `demo-data/organizations.json` once at startup and refuses to start on an unknown type. Whether a hospital is approved still comes from the Authority's own decisions (HC-131), not from this file.
2. **A role is held at an organization that fits it** (`domain/organization_identity.py`):

   | Role | Organization types |
   |---|---|
   | `governance_reviewer` | `governance_authority`, and only the one this Node runs for (`NodeIdentity.organization_ref`) |
   | `hospital_manager`, `physician` | `hospital`, `private_practice` |
   | `researcher` | `research_institution` |
   | any other role | any known organization (the role grants nothing here anyway) |

   An unknown organization, or one that does not fit, grants nothing. The check runs in `authorize` on every protected route, after the role check, and answers the same `403 permission_denied`, so no new denial code is needed on the read routes.
3. **A person acts only for their own organization.** A synchronization request's `requester_organization_ref` and a research request's `research_organization_ref` must be the signed-in person's organization: `403 organization_mismatch` otherwise, checked after `submitter_mismatch` and before anything is recorded. Synchronization requests 1.5.0 and research requests 1.4.0 add the code; hospital approval 1.3.1, audit events 1.1.1, and ledger proofs 1.3.1 note the reviewer case in their wording.
4. **Reviewers stay cross-organization readers.** The Authority reviews every institution's applications and requests; that is its role, and the conflict-of-interest rules of HC-131/132/133 still forbid deciding on one's own organization.
5. **Same switch as HC-211 and HC-212.** Enforcement applies only with `GOVERNANCE_AUTH=required`; off, the default, declared organizations are trusted, as before.

## Alternatives considered

- **Verifying institutions with certificates or signed Node identities:** the production answer for Node-to-Node trust, but it identifies services, and needs key management. HC-214's subject.
- **Taking the organization from the session and dropping it from submission bodies:** simpler for callers, but a breaking contract change, and the field remains meaningful when authentication is off. Rejected for a minor version; the body must match the session instead.
- **A distinct `affiliation_not_recognized` code:** more precise, but it would add a code to every protected route's contract for a case the demo data never produces. Rejected; the detail says why.
- **Restricting requesters to read their own organization's requests:** useful, but it adds a permission and read routes for non-reviewers; no ticket asks for it yet.
- **Gating submissions on the requester organization's approval:** the synchronization review already fails its `organizations` check for an unapproved organization; blocking at submission would hide the request from the Authority.

## Consequences

### Positive

- With authentication required, a submission speaks for the signed-in person's own institution, and only the Authority the Node runs for can review there: not a hospital, not the platform company.
- One domain rule, one port, no new dependency; testable without network or databases.

### Negative

- Off by default, like HC-211 and HC-212.
- Organizations and affiliations come from fictional demo files, held by the Node, changed only by editing them: not a verified institution registry, and not federated from each organization's own identity provider.
- A person has one organization; multiple affiliations are not modelled.
- The principal investigator named by a research request is not checked against the research organization.
- Denials are not audited (HC-215); the service authorization checks stay unauthenticated (HC-214).

## Follow-up

- HC-214: signed federation authorization, so Nodes and services prove which organization they are.
- HC-215: audit of denials, in the threat model.
- The Governance Portal and the Hospital Nodes using the Node's sessions in place of HC-210's browser-side personas.
- An institution registry fed by the Authority's own onboarding decisions, when persistence is decided.
