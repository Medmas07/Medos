# Scripts

Add small, documented, repeatable project scripts here after the selected stack creates a concrete need. Scripts must fail clearly and must not embed secrets.

Future tooling should expose consistent equivalents of the following lifecycle commands when supported by the selected stack:

- `dev`: run a development environment.
- `build`: create optimized deployable artifacts.
- `preview`: run those artifacts in a local production-like environment.
- `test`: execute automated tests.
- `lint`: run static and formatting checks.
- `validate`: perform the applicable lint, test, build, preview, integration, and E2E checks.
- `deploy`: perform an explicitly authorized deployment.

These are naming conventions, not implemented commands. Do not add fictitious npm or Python scripts. Deployment must remain separate from CI validation and must never run without explicit authorization.
