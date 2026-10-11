# Deployment

Deployment architecture and hosting remain undecided. This documentation defines the validation approach and records candidates without configuring remote services.

- [Environments](environments.md) distinguishes development, preview, and production.
- [Production and preview guide](../../production/README.md) describes local validation and the generic deployment checklist.

Every backend runtime, including AI Services, uses Python + FastAPI ([ADR-0003](../decisions/ADR-0003-backend-runtime-strategy.md)). AI libraries and the AI hosting strategy are not decided. The Hospital Node's container image is decided by [ADR-0016](../decisions/ADR-0016-hospital-node-container-image.md) (HC-220). Future decisions about frontend hosting, backend hosting, AI service hosting, containers for the other runtimes, image registry, tunnels, database hosting, and deployment topology require ADRs.

No automatic deployment workflow should be added until the hosting strategy is accepted. CI validation and production deployment must remain separate.
