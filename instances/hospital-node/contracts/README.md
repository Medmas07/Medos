# Hospital Node Contracts

## Purpose and status

PLANNED location for contracts owned internally by the Hospital Node boundary. No contract or clinical schema is defined.

## Responsibilities and communication boundaries

Future Node-local contract documents may live here. Ports are code owned by `application/` ([ADR-0003](../../../docs/decisions/ADR-0003-backend-runtime-strategy.md)): the DMI port is [`application/dmi_source.py`](../application/dmi_source.py) (HC-120), not a document here. Cross-component API, event, schema, and Federation definitions remain in repository-level `/contracts`.

## Non-responsibilities

This directory does not centralize clinical domain models, publish another component's persistence schema, or replace repository-level communication contracts.
