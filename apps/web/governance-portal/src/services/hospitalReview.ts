/**
 * Hospital approval review (HC-073, D1).
 *
 * Pure rules for a governance reviewer's decision on a hospital application. The
 * decision is SIMULATED: it is built here and kept in local portal state
 * (reviewStore). The Governance Node decision API (HC-131) is PLANNED; nothing is
 * sent to it or persisted.
 */
import type {
  GovernanceAuditEvent,
  GovernanceDecision,
  HospitalAgreement,
  HospitalApplication,
  HospitalDocument,
  PersonInfo,
} from '../types/governance'

export const MIN_RATIONALE_LENGTH = 20

export type ReviewOutcome = 'approved' | 'rejected'

export interface ReviewDraft {
  outcome: ReviewOutcome | null
  rationale: string
  /** One condition per entry; blank entries are ignored. */
  conditions: string[]
  /** The reviewer confirms having examined every finding listed for the application. */
  findingsAcknowledged: boolean
}

export const emptyDraft: ReviewDraft = {
  outcome: null,
  rationale: '',
  conditions: [],
  findingsAcknowledged: false,
}

export interface ReviewFindings {
  missingDocuments: HospitalDocument[]
  unacceptedAgreements: HospitalAgreement[]
  /** Deterministic completeness check. */
  completenessFindings: string[]
  /** Mocked, advisory AI review. Never binding. */
  advisoryFindings: string[]
}

export type ReviewField = 'application' | 'reviewer' | 'outcome' | 'rationale' | 'acknowledgement' | 'conditions'

export interface ReviewIssue {
  field: ReviewField
  message: string
}

export interface RecordedReview {
  application: HospitalApplication
  decision: GovernanceDecision
  auditEvent: GovernanceAuditEvent
}

export function reviewFindings(application: HospitalApplication): ReviewFindings {
  const findingsOf = (step: string) =>
    application.reviewSteps.find((s) => s.step === step)?.findings ?? []
  return {
    missingDocuments: application.documents.filter((d) => d.status !== 'received'),
    unacceptedAgreements: application.agreements.filter((a) => !a.accepted),
    completenessFindings: findingsOf('completeness_check'),
    advisoryFindings: findingsOf('assisted_review'),
  }
}

export function hasFindings(findings: ReviewFindings): boolean {
  return (
    findings.missingDocuments.length > 0 ||
    findings.unacceptedAgreements.length > 0 ||
    findings.completenessFindings.length > 0 ||
    findings.advisoryFindings.length > 0
  )
}

export function isAwaitingReview(application: HospitalApplication): boolean {
  return application.status === 'human_review' && application.decisionId === null
}

function cleanConditions(conditions: string[]): string[] {
  return conditions.map((c) => c.trim()).filter((c) => c.length > 0)
}

/**
 * Every rule a decision must satisfy. An empty list means the decision may be recorded.
 * Only a governance reviewer from outside the applicant organization may decide: an
 * applicant never approves its own request.
 */
export function validateReview(
  application: HospitalApplication,
  draft: ReviewDraft,
  reviewer: PersonInfo | undefined,
): ReviewIssue[] {
  const issues: ReviewIssue[] = []
  if (!isAwaitingReview(application)) {
    issues.push({ field: 'application', message: 'Ce dossier a déjà fait l’objet d’une décision.' })
  }
  if (!reviewer || reviewer.role !== 'governance_reviewer') {
    issues.push({
      field: 'reviewer',
      message: 'Seul un réviseur de l’Autorité de gouvernance peut statuer.',
    })
  } else if (reviewer.organizationId === application.organizationId) {
    issues.push({
      field: 'reviewer',
      message: 'Un membre de l’établissement demandeur ne peut pas statuer sur son propre dossier.',
    })
  }
  if (draft.outcome === null) {
    issues.push({ field: 'outcome', message: 'Choisissez d’approuver ou de rejeter le dossier.' })
  }
  if (draft.rationale.trim().length < MIN_RATIONALE_LENGTH) {
    issues.push({
      field: 'rationale',
      message: `La motivation doit compter au moins ${MIN_RATIONALE_LENGTH} caractères.`,
    })
  }
  const findings = reviewFindings(application)
  if (hasFindings(findings) && !draft.findingsAcknowledged) {
    issues.push({
      field: 'acknowledgement',
      message: 'Confirmez avoir examiné chaque point relevé avant de statuer.',
    })
  }
  const incomplete = findings.missingDocuments.length > 0 || findings.unacceptedAgreements.length > 0
  if (draft.outcome === 'approved' && incomplete && cleanConditions(draft.conditions).length === 0) {
    issues.push({
      field: 'conditions',
      message: 'Une approbation d’un dossier incomplet doit fixer au moins une condition.',
    })
  }
  return issues
}

export class InvalidReview extends Error {
  readonly issues: ReviewIssue[]

  constructor(issues: ReviewIssue[]) {
    super(issues.map((i) => i.message).join(' '))
    this.issues = issues
  }
}

/**
 * Builds the simulated decision, its audit event, and the updated application.
 * Throws InvalidReview if any rule fails. The audit event carries references only.
 */
export function recordReview(
  application: HospitalApplication,
  draft: ReviewDraft,
  reviewer: PersonInfo | undefined,
  at: Date,
  sequence: number,
): RecordedReview {
  const issues = validateReview(application, draft, reviewer)
  if (issues.length > 0 || !reviewer || draft.outcome === null) {
    throw new InvalidReview(issues)
  }
  const decidedAt = at.toISOString()
  const subject = application.id.replace(/^app-/, '')
  const decision: GovernanceDecision = {
    id: `dec-sim-${subject}-${sequence}`,
    subjectType: 'hospital_application',
    subjectId: application.id,
    outcome: draft.outcome,
    decidedById: reviewer.id,
    decidedAt,
    rationale: draft.rationale.trim(),
    conditions: draft.outcome === 'approved' ? cleanConditions(draft.conditions) : [],
    validUntil: null,
    simulated: true,
  }
  const auditEvent: GovernanceAuditEvent = {
    id: `evt-sim-${sequence}`,
    at: decidedAt,
    actorId: reviewer.id,
    action: 'decision_recorded',
    subjectType: 'decision',
    subjectId: decision.id,
    organizationIds: ['org-governance', application.organizationId],
    simulated: true,
  }
  return {
    decision,
    auditEvent,
    application: {
      ...application,
      status: draft.outcome,
      decisionId: decision.id,
      reviewSteps: application.reviewSteps.map((step) =>
        step.step === 'human_review'
          ? { ...step, status: 'completed', reviewerId: reviewer.id, completedAt: decidedAt }
          : step,
      ),
    },
  }
}
