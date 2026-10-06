# Deployment

Deployment architecture and hosting remain undecided. This documentation defines the validation approach and records candidates without configuring remote services.

- [Environments](environments.md) distinguishes development, preview, and production.
- [Production and preview guide](../../production/README.md) describes local validation and the generic deployment checklist.

Python is confirmed for potential AI/ML components, but an AI framework, service boundary, and hosting strategy are not. Future decisions about frontend hosting, backend hosting, AI service hosting, Docker, tunnels, database hosting, and deployment topology require ADRs.

No automatic deployment workflow should be added until the hosting strategy is accepted. CI validation and production deployment must remain separate.
