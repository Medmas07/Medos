# Governance Node

The autonomous Ethics / Governance runtime boundary. Future concerns may include the hospital registry, institution validation, policy evaluation, synchronization and research authorization, consent governance, audit, and an immutable-ledger adapter.

Ledger interaction belongs behind an application-owned `AuditLedgerPort`; blockchain is an adapter detail and never stores raw medical data. No ledger, framework, or database is initialized here.
