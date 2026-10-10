/**
 * Approve or reject a synchronization request (HC-076, D1).
 *
 * Pure rules for a governance reviewer's decision on an inter-hospital synchronization.
 * Deterministic checks (organizations, consent basis, duration) decide whether approval
 * is possible; the reviewer decides. The decision is SIMULATED: it is kept in local
 * portal state (reviewStore). The Governance Node synchronization API (HC-132) is
 * PLANNED, and no Hospital Node learns of the decision.
 */
import type {
  AccessGrant,
  GovernanceAuditEvent,
  GovernanceDecision,
  OrganizationInfo,
  PersonInfo,
  SynchronizationRequest,
} from '../types/governance'
import { MIN_RATIONALE_LENGTH, type ReviewOutcome } from './hospitalReview'

const DAY_MS = 24 * 60 * 60 * 1000

export type SyncCheckState = 'pass' | 'fail' | 'manual'

export interface SyncCheck {
  id: 'organizations' | 'consent' | 'duration'
  label: string
  state: SyncCheckState
  detail: string
}

export interface SyncReviewContext {
  request: SynchronizationRequest
  requester: OrganizationInfo | undefined
  target: OrganizationInfo | undefined
  /** The grant named by the consent, when its basis is a patient grant. */
  grant: AccessGrant | undefined
  now: Date
}

export interface SyncReviewDraft {
  outcome: ReviewOutcome | null
  rationale: string
  conditions: string[]
  /** Days the authorization lasts if approved; at most maxApprovedDays. */
  approvedDays: number
  /** The reviewer confirms the checks the portal cannot verify itself. */
  manualChecksConfirmed: boolean
}

export type SyncReviewField = 'request' | 'reviewer' | 'outcome' | 'rationale' | 'checks' | 'manual' | 'duration'

export interface SyncReviewIssue {
  field: SyncReviewField
  message: string
}

export interface RecordedSyncReview {
  request: SynchronizationRequest
  decision: GovernanceDecision
  auditEvent: GovernanceAuditEvent
}

const formatDate = (iso: string) => new Date(iso).toLocaleDateString('fr-TN')

function grantProblem(context: SyncReviewContext): string | null {
  const { request, grant, now } = context
  if (!grant) return `L’autorisation ${request.consent.accessGrantId ?? '(non référencée)'} est introuvable.`
  if (grant.status === 'revoked' || grant.revokedAt) return `L’autorisation ${grant.id} a été révoquée.`
  if (grant.status !== 'active' || new Date(grant.expiresAt) <= now) {
    return `L’autorisation ${grant.id} a expiré le ${formatDate(grant.expiresAt)}.`
  }
  if (grant.patientId !== request.patientId) return `L’autorisation ${grant.id} concerne un autre patient.`
  const uncovered = request.scope.filter((item) => !grant.scope.includes(item))
  if (uncovered.length > 0) {
    return `L’autorisation ${grant.id} ne couvre pas : ${uncovered.join(', ')}.`
  }
  return null
}

/**
 * The longest authorization the reviewer may grant: the requested duration, never
 * beyond the patient grant the synchronization relies on. 0 means none is possible.
 */
export function maxApprovedDays(context: SyncReviewContext): number {
  const { request, grant, now } = context
  if (request.consent.basis !== 'patient_grant' || !grant) return request.durationDays
  const daysLeft = Math.floor((new Date(grant.expiresAt).getTime() - now.getTime()) / DAY_MS)
  return Math.max(0, Math.min(request.durationDays, daysLeft))
}

export function syncChecks(context: SyncReviewContext): SyncCheck[] {
  const { request, requester, target } = context

  const orgsApproved =
    requester?.governanceStatus === 'approved' &&
    target?.governanceStatus === 'approved' &&
    request.requesterOrganizationId !== request.targetOrganizationId
  const organizations: SyncCheck = {
    id: 'organizations',
    label: 'Établissements agréés',
    state: orgsApproved ? 'pass' : 'fail',
    detail: orgsApproved
      ? `${requester?.shortName} et ${target?.shortName} sont agréés par l’Autorité.`
      : 'Le demandeur et le détenteur doivent être deux établissements distincts agréés.',
  }

  let consent: SyncCheck
  if (request.consent.basis === 'none') {
    consent = {
      id: 'consent',
      label: 'Base d’autorisation',
      state: 'fail',
      detail: 'Aucune autorisation du patient ni base légale n’est fournie.',
    }
  } else if (request.consent.basis === 'patient_grant') {
    const problem = grantProblem(context)
    consent = {
      id: 'consent',
      label: 'Autorisation du patient',
      state: problem ? 'fail' : 'pass',
      detail:
        problem ??
        `${context.grant?.id} est active jusqu’au ${formatDate(context.grant!.expiresAt)} et couvre le périmètre demandé.`,
    }
  } else {
    consent = {
      id: 'consent',
      label: 'Base d’autorisation',
      state: 'manual',
      detail:
        request.consent.basis === 'signed_consent_form'
          ? 'Consentement signé : le document n’est pas vérifiable dans le portail.'
          : 'Dérogation d’urgence : la justification n’est pas vérifiable dans le portail.',
    }
  }

  const max = maxApprovedDays(context)
  const duration: SyncCheck = {
    id: 'duration',
    label: 'Durée',
    state: max >= 1 ? 'pass' : 'fail',
    detail:
      max >= request.durationDays
        ? `${request.durationDays} jours demandés.`
        : max >= 1
          ? `${request.durationDays} jours demandés, limités à ${max} jours par l’expiration de l’autorisation du patient.`
          : 'Aucune durée possible avant l’expiration de l’autorisation du patient.',
  }

  return [organizations, consent, duration]
}

export function initialSyncDraft(context: SyncReviewContext): SyncReviewDraft {
  return {
    outcome: null,
    rationale: '',
    conditions: [],
    approvedDays: maxApprovedDays(context),
    manualChecksConfirmed: false,
  }
}

const cleanConditions = (conditions: string[]) =>
  conditions.map((c) => c.trim()).filter((c) => c.length > 0)

/**
 * Every rule the decision must satisfy. Approval needs every check to pass (or be
 * confirmed by the reviewer when it cannot be verified here); a rejection is always
 * possible. Nobody from the requesting or target organization may decide.
 */
export function validateSyncReview(
  context: SyncReviewContext,
  draft: SyncReviewDraft,
  reviewer: PersonInfo | undefined,
): SyncReviewIssue[] {
  const { request } = context
  const issues: SyncReviewIssue[] = []
  if (request.status !== 'pending' || request.decisionId !== null) {
    issues.push({ field: 'request', message: 'Cette demande a déjà fait l’objet d’une décision.' })
  }
  if (!reviewer || reviewer.role !== 'governance_reviewer') {
    issues.push({ field: 'reviewer', message: 'Seul un réviseur de l’Autorité de gouvernance peut statuer.' })
  } else if (
    reviewer.organizationId === request.requesterOrganizationId ||
    reviewer.organizationId === request.targetOrganizationId
  ) {
    issues.push({
      field: 'reviewer',
      message: 'Un membre d’un établissement concerné ne peut pas statuer sur cette demande.',
    })
  }
  if (draft.outcome === null) {
    issues.push({ field: 'outcome', message: 'Choisissez d’autoriser ou de refuser la synchronisation.' })
  }
  if (draft.rationale.trim().length < MIN_RATIONALE_LENGTH) {
    issues.push({
      field: 'rationale',
      message: `La motivation doit compter au moins ${MIN_RATIONALE_LENGTH} caractères.`,
    })
  }
  if (draft.outcome === 'approved') {
    const checks = syncChecks(context)
    const failed = checks.filter((c) => c.state === 'fail')
    if (failed.length > 0) {
      issues.push({
        field: 'checks',
        message: `Autorisation impossible : ${failed.map((c) => c.label.toLowerCase()).join(', ')} non conforme(s). Seul un refus est possible.`,
      })
    }
    if (checks.some((c) => c.state === 'manual') && !draft.manualChecksConfirmed) {
      issues.push({
        field: 'manual',
        message: 'Confirmez avoir vérifié la base d’autorisation hors du portail.',
      })
    }
    const max = maxApprovedDays(context)
    if (failed.length === 0 && (!Number.isInteger(draft.approvedDays) || draft.approvedDays < 1 || draft.approvedDays > max)) {
      issues.push({ field: 'duration', message: `La durée autorisée doit être comprise entre 1 et ${max} jours.` })
    }
  }
  return issues
}

export class InvalidSyncReview extends Error {
  readonly issues: SyncReviewIssue[]

  constructor(issues: SyncReviewIssue[]) {
    super(issues.map((i) => i.message).join(' '))
    this.issues = issues
  }
}

/**
 * Builds the simulated decision, its audit event (references only), and the updated
 * request. An approval is temporary: it ends approvedDays after the decision.
 */
export function recordSyncReview(
  context: SyncReviewContext,
  draft: SyncReviewDraft,
  reviewer: PersonInfo | undefined,
  sequence: number,
): RecordedSyncReview {
  const issues = validateSyncReview(context, draft, reviewer)
  if (issues.length > 0 || !reviewer || draft.outcome === null) {
    throw new InvalidSyncReview(issues)
  }
  const { request, now } = context
  const approved = draft.outcome === 'approved'
  const conditions = approved ? cleanConditions(draft.conditions) : []
  if (approved && draft.approvedDays < request.durationDays) {
    conditions.unshift(`Durée autorisée : ${draft.approvedDays} jours (demandée : ${request.durationDays} jours).`)
  }
  const decision: GovernanceDecision = {
    id: `dec-sim-${request.id}-${sequence}`,
    subjectType: 'synchronization_request',
    subjectId: request.id,
    outcome: draft.outcome,
    decidedById: reviewer.id,
    decidedAt: now.toISOString(),
    rationale: draft.rationale.trim(),
    conditions,
    validUntil: approved ? new Date(now.getTime() + draft.approvedDays * DAY_MS).toISOString() : null,
    simulated: true,
  }
  return {
    decision,
    auditEvent: {
      id: `evt-sim-${sequence}`,
      at: decision.decidedAt,
      actorId: reviewer.id,
      action: 'decision_recorded',
      subjectType: 'decision',
      subjectId: decision.id,
      organizationIds: ['org-governance', request.requesterOrganizationId, request.targetOrganizationId],
      simulated: true,
    },
    request: { ...request, status: draft.outcome, decisionId: decision.id },
  }
}
