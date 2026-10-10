# Project workflow

## Delivery flow

`Issue -> Ready -> self-assignment -> branch -> implementation -> tests -> Pull Request -> review -> validation -> merge -> Done`

See [the contribution guide](../CONTRIBUTING.md) for branch, commit, and review conventions.

## Recommended GitHub Project configuration

| Field | Values |
| --- | --- |
| Status | Backlog, Ready, In Progress, Blocked, In Review, Testing, Done |
| Priority | P0, P1, P2, P3 |
| Type | Feature, Bug, Task, Research, Architecture, Design, DevOps, Docs, Test |
| Effort | XS, S, M, L, XL |
| MVP | Yes, No |

## Automated status synchronization

The repository workflow keeps dependency-related Project statuses synchronized:

- self-assignment moves an open issue to `In Progress` and creates its linked branch when needed;
- closing an issue moves that issue to `Done`;
- closing or reopening an issue recalculates every open issue that references it under `Blocked by:`;
- an issue stays `Blocked` while at least one referenced dependency is open;
- when all dependencies close, only an item currently marked `Blocked` moves to `Ready` (or `Todo` when the Project has no `Ready` option), so active work is not overwritten;
- reopening an issue recalculates that issue from its own `Blocked by:` section.

Dependency references must use list entries such as `- #123` between the exact `Blocked by:` and `Blocks:` headings. A missing referenced issue is treated conservatively as an unresolved dependency.

The remote GitHub Project must not be created or changed without explicit authorization.
