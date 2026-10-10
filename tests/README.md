# Cross-System Tests

- [`contracts/`](contracts/): IMPLEMENTED. Checks every API contract under [`contracts/api/`](../contracts/api/README.md): each must be valid OpenAPI, and each embedded example must match its schema. It also tests the medication safety contract's boundary rules (an LLM cannot be the safety source, results stay pending clinician review, outcome and warnings agree). Run it from `tests/contracts/` with `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pytest`. CI runs it when contracts change.
- `integration/` and `e2e/`: PLANNED, empty placeholders for cross-service integration, Federation, deployment, and end-to-end journey tests.
