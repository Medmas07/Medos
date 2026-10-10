# Clinician App

## Purpose and status

PLANNED mobile product for authorized clinician workflows serving physicians, nurses, and clinics. Flutter + Dart and an Android-first development path are CONFIRMED by [ADR-0002](../../../docs/decisions/ADR-0002-mobile-technology.md). No dependencies, generated platform project, or application code exists.

## Responsibilities and owned concepts

- Authorized patient lists, longitudinal views, consultation workspace, alerts, and priority presentation.
- Consent-aware speech-to-text, adaptive intake, extraction review, lab review, and medication-warning presentation.

## Communication boundaries

The Clinician App consumes authorized context through explicit APIs and never accesses hospital databases directly. Clinical AI output is advisory and subject to clinician review.

## Non-responsibilities

It does not have autonomous diagnostic or prescription authority, make Governance decisions, or treat LLM output as validated clinical truth.

## Expected contracts

PLANNED authorization, patient-view, consultation, extraction-review, medication-safety, alert, queue, and notification contracts.
