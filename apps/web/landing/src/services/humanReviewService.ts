import type { ApplicationDocument, HospitalApplication, OnboardingSnapshot, PortalNotification } from '../types/onboarding'
import { documentChecklist } from './documentService'

/**
 * Human validation state (HC-058), as the hospital sees it. Human review belongs
 * to the Governance / Ethics Authority: the portal only displays its state and
 * offers no way to act on, speed up, or decide the review. The reviewer's
 * identity is not shown, only that a reviewer is assigned. Refreshing the state
 * is MOCKED: it re-reads the local snapshot after a simulated delay.
 */

export type HumanReviewState =
  /** No application, or a draft not yet submitted. */
  | { kind: 'not_submitted' }
  /** Submitted, but no human-review step was recorded (application handled before it existed). */
  | { kind: 'not_recorded' }
  | { kind: 'pending'; reviewerAssigned: boolean; submittedAt: string }
  | { kind: 'completed'; completedAt: string | null; decided: boolean }

/** Derives the human-review state from the application. Pure. */
export function humanReviewState(application: HospitalApplication | null): HumanReviewState {
  if (!application || application.status === 'draft') return { kind: 'not_submitted' }
  const step = application.reviewSteps.find((s) => s.step === 'human_review')
  if (!step) return { kind: 'not_recorded' }
  if (step.status === 'pending') {
    return { kind: 'pending', reviewerAssigned: Boolean(step.reviewerId), submittedAt: application.submittedAt }
  }
  return { kind: 'completed', completedAt: step.completedAt, decided: application.decisionId !== null }
}

/** Documents still expected from the hospital while the review is open. Pure. */
export function outstandingDocuments(application: HospitalApplication): ApplicationDocument[] {
  return documentChecklist(application).filter((d) => d.status !== 'received')
}

/** Documents deposited in the portal after the dossier was submitted. Pure. */
export function supplementsSinceSubmission(application: HospitalApplication): ApplicationDocument[] {
  const submittedAt = new Date(application.submittedAt).getTime()
  return application.documents.filter((d) => d.upload && new Date(d.upload.uploadedAt).getTime() > submittedAt)
}

/** Notifications about this application, newest first. Pure. */
export function applicationNotifications(snapshot: OnboardingSnapshot): PortalNotification[] {
  const id = snapshot.application?.id
  return id ? snapshot.notifications.filter((n) => n.relatedId === id) : []
}

export interface RefreshOptions {
  /** Simulates an unavailable service (demo scenario). */
  simulateFailure?: boolean
  delayMs?: number
  now?: Date
}

/**
 * Simulated status refresh. With no Governance Node to ask yet, it returns the
 * state already known, with the time it was checked.
 */
export async function refreshReviewState(
  snapshot: OnboardingSnapshot,
  { simulateFailure = false, delayMs = 600, now = new Date() }: RefreshOptions = {},
): Promise<{ state: HumanReviewState; checkedAt: string }> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("Le statut n'a pas pu être actualisé : service d'adhésion simulé indisponible (scénario de démonstration).")
  }
  return { state: humanReviewState(snapshot.application), checkedAt: now.toISOString() }
}
