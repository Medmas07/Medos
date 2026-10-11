# API documentation

Status: no explanatory material yet. Every backend runtime exposes HTTP/JSON through FastAPI ([ADR-0003](../decisions/ADR-0003-backend-runtime-strategy.md)), and every cross-component API is specified as a versioned OpenAPI 3.1 file in [`contracts/`](../../contracts/README.md), checked by the [contract tests](../../tests/contracts/). Each runtime's README documents how to run it and which contracts it serves. Add guides here only when they explain something those files do not. Transport security and service authentication remain OPEN.
