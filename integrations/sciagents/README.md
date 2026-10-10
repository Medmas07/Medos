# SciAgents Integration

## Purpose and status

SciAgents exists externally. This repository owns only its PLANNED integration; no client or communication contract is implemented.

## Responsibilities and owned concepts

Client adapter, authentication boundary, request/response mapping, timeouts, error mapping, experiment provenance, and Research Portal integration.

## Communication boundaries

The Research Service/Portal communicates through provider-neutral contracts; SciAgents-specific details remain in this adapter boundary.

## Non-responsibilities

This repository does not own or reimplement SciAgents, and SciAgents output does not automatically become clinical truth.

## Expected contracts

PLANNED investigation-request, evidence/hypothesis/contradiction/citation result, provenance, authentication, timeout, and error contracts.
