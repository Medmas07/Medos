# Contributing

## Workflow

`Issue -> Ready -> self-assignment -> branch -> implementation -> tests -> Pull Request -> review -> validation -> merge -> Done`

Do not begin implementation until the issue is sufficiently defined and Ready. Keep the GitHub Project status synchronized when one exists.

## Branches

Use `<type>/<issue-number>-<short-description>` with one of:

- `feat`, `fix`, `docs`, `research`, `architecture`
- `devops`, `refactor`, `test`

Example: `docs/12-record-api-options`.

## Commits

Use `type(scope): concise description`. Allowed types are `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`, `research`, and `architecture`.

## Pull requests

Use the pull request template, link the issue, keep scope focused, and include validation evidence. Obtain review before merging. Significant technical choices require an ADR.

## Recommended GitHub Project fields

- Status: Backlog, Ready, In Progress, Blocked, In Review, Testing, Done
- Priority: P0, P1, P2, P3
- Type: Feature, Bug, Task, Research, Architecture, Design, DevOps, Docs, Test
- Effort: XS, S, M, L, XL
- MVP: Yes, No

Creating or changing a remote Project requires explicit authorization.
