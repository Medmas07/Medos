/**
 * Research access request review (HC-078, D1).
 *
 * Pure rules for the Governance / Ethics Authority's decision on a research project's
 * data-access request. An approval authorizes Compute-to-Data execution only, and says
 * exactly what it covers: the organizations, the variables, the end date, and the
 * minimum cell size of any output, as the Authorization and output policy of
 * contracts/api/research/research-node-execution.v1.yaml expect.
 *
 * The decision is SIMULATED: it is kept in local portal state (reviewStore). The
 * Governance Node research API (HC-133) is PLANNED; no Research Service or Hospital Node
 * learns of the decision.
 */
import type {
  GovernanceAuditEvent,
  GovernanceDecision,
  OrganizationInfo,
  PersonInfo,
  ResearchAccessRequest,
  ResearchProject,
} from '../types/governance'
import { MIN_RATIONALE_LENGTH, type ReviewOutcome } from './hospitalReview'

/** D1 demo policy: the smallest output cell the Authority accepts (as in dec-rar-001). */
export const MINIMUM_CELL_SIZE_FLOOR = 10
/** D1 demo policy: the longest research authorization, in months (as in dec-rar-001). */
export const MAX_VALIDITY_MONTHS = 12

export type ResearchCheckState = 'pass' | 'fail'

export interface ResearchCheck {
  id: 'project' | 'protocol' | 'scope' | 'organizations'
  label: string
  state: ResearchCheckState
  detail: string
}

export interface ResearchReviewContext {
  request: ResearchAccessRequest
  project: ResearchProject | undefined
  organization: (id: string) => OrganizationInfo | undefined
  now: Date
}

export interface ResearchReviewDraft {
  outcome: ReviewOutcome | null
  rationale: string
  conditions: string[]
  approvedOrganizationIds: string[]
  approvedVariables: string[]
  validityMonths: number
  minimumCellSize: number
}

export type ResearchReviewField =
  | 'request'
  | 'reviewer'
  | 'outcome'
  | 'rationale'
  | 'checks'
  | 'organizations'
  | 'variables'
  | 'validity'
  | 'cellSize'

export interface ResearchReviewIssue {
  field: ResearchReviewField
  message: string
}

export interface RecordedResearchReview {
  request: ResearchAccessRequest
  decision: GovernanceDecision
  auditEvent: GovernanceAuditEvent
}

/** A participating organization data may come from: approved, with a Hospital Node. */
export function isEligibleOrganization(org: OrganizationInfo | undefined): boolean {
  return org?.governanceStatus === 'approved' && Boolean(org.node)
}

export function eligibleOrganizationIds(context: ResearchReviewContext): string[] {
  return (context.project?.participatingOrganizationIds ?? []).filter((id) =>
    isEligibleOrganization(context.organization(id)),
  )
}

export function researchChecks(context: ResearchReviewContext): ResearchCheck[] {
  const { request, project } = context
  const linked = Boolean(project && project.id === request.projectId && project.researchAccessRequestId === request.id)
  const eligible = eligibleOrganizationIds(context)
  const excluded = (project?.participatingOrganizationIds ?? []).filter((id) => !eligible.includes(id))
  const name = (id: string) => context.organization(id)?.shortName ?? id
  return [
    {
      id: 'project',
      label: 'Projet rattaché',
      state: linked ? 'pass' : 'fail',
      detail: linked ? `${project!.title} (${project!.id}).` : 'La demande ne correspond à aucun projet connu.',
    },
    {
      id: 'protocol',
      label: 'Protocole',
      state: project?.protocolDocument ? 'pass' : 'fail',
      detail: project?.protocolDocument
        ? `${project.protocolDocument.title} fourni.`
        : 'Aucun protocole n’est joint à la demande.',
    },
    {
      id: 'scope',
      label: 'Population et variables',
      state: project?.population.trim() && project.variables.length > 0 ? 'pass' : 'fail',
      detail:
        project?.population.trim() && project.variables.length > 0
          ? `${project.variables.length} variable(s) demandée(s) sur une population définie.`
          : 'La population ou les variables demandées ne sont pas définies.',
    },
    {
      id: 'organizations',
      label: 'Établissements participants',
      state: eligible.length > 0 ? 'pass' : 'fail',
      detail:
        eligible.length === 0
          ? 'Aucun établissement participant n’est agréé avec un nœud.'
          : excluded.length > 0
            ? `${eligible.map(name).join(', ')} agréé(s) ; ${excluded.map(name).join(', ')} exclu(s), non agréé(s) ou sans nœud.`
            : `${eligible.map(name).join(', ')} agréé(s) par l’Autorité avec un nœud.`,
    },
  ]
}

export function initialResearchDraft(context: ResearchReviewContext): ResearchReviewDraft {
  return {
    outcome: null,
    rationale: '',
    conditions: [],
    approvedOrganizationIds: eligibleOrganizationIds(context),
    approvedVariables: [...(context.project?.variables ?? [])],
    validityMonths: MAX_VALIDITY_MONTHS,
    minimumCellSize: MINIMUM_CELL_SIZE_FLOOR,
  }
}

/** The end of an authorization lasting `months` calendar months from `from`. */
export function validUntil(from: Date, months: number): Date {
  const end = new Date(from)
  end.setUTCMonth(end.getUTCMonth() + months)
  return end
}

/**
 * Every rule the decision must satisfy. An approval may only narrow the request: a
 * subset of its eligible organizations and of its variables. Nobody from the research
 * organization, a participating organization, or the investigator may decide.
 */
export function validateResearchReview(
  context: ResearchReviewContext,
  draft: ResearchReviewDraft,
  reviewer: PersonInfo | undefined,
): ResearchReviewIssue[] {
  const { request, project } = context
  const issues: ResearchReviewIssue[] = []
  if (request.status !== 'under_review' || request.decisionId !== null) {
    issues.push({ field: 'request', message: 'Cette demande a déjà fait l’objet d’une décision.' })
  }
  if (!reviewer || reviewer.role !== 'governance_reviewer') {
    issues.push({ field: 'reviewer', message: 'Seul un réviseur de l’Autorité de gouvernance peut statuer.' })
  } else if (
    reviewer.id === request.submittedById ||
    reviewer.id === project?.principalInvestigatorId ||
    reviewer.organizationId === project?.organizationId ||
    project?.participatingOrganizationIds.includes(reviewer.organizationId ?? '')
  ) {
    issues.push({
      field: 'reviewer',
      message: 'Un membre de l’équipe de recherche ou d’un établissement participant ne peut pas statuer.',
    })
  }
  if (draft.outcome === null) {
    issues.push({ field: 'outcome', message: 'Choisissez d’approuver ou de rejeter la demande.' })
  }
  if (draft.rationale.trim().length < MIN_RATIONALE_LENGTH) {
    issues.push({
      field: 'rationale',
      message: `La motivation doit compter au moins ${MIN_RATIONALE_LENGTH} caractères.`,
    })
  }
  if (draft.outcome !== 'approved') return issues

  const failed = researchChecks(context).filter((c) => c.state === 'fail')
  if (failed.length > 0) {
    issues.push({
      field: 'checks',
      message: `Approbation impossible : ${failed.map((c) => c.label.toLowerCase()).join(', ')} non conforme(s). Seul un rejet est possible.`,
    })
  }
  const eligible = eligibleOrganizationIds(context)
  if (draft.approvedOrganizationIds.length === 0 || draft.approvedOrganizationIds.some((id) => !eligible.includes(id))) {
    issues.push({ field: 'organizations', message: 'Autorisez au moins un établissement participant agréé.' })
  }
  const requested = project?.variables ?? []
  if (draft.approvedVariables.length === 0 || draft.approvedVariables.some((v) => !requested.includes(v))) {
    issues.push({ field: 'variables', message: 'Autorisez au moins une des variables demandées.' })
  }
  if (!Number.isInteger(draft.validityMonths) || draft.validityMonths < 1 || draft.validityMonths > MAX_VALIDITY_MONTHS) {
    issues.push({ field: 'validity', message: `La durée doit être comprise entre 1 et ${MAX_VALIDITY_MONTHS} mois.` })
  }
  if (!Number.isInteger(draft.minimumCellSize) || draft.minimumCellSize < MINIMUM_CELL_SIZE_FLOOR) {
    issues.push({
      field: 'cellSize',
      message: `L’effectif minimal par cellule doit être un entier d’au moins ${MINIMUM_CELL_SIZE_FLOOR}.`,
    })
  }
  return issues
}

export class InvalidResearchReview extends Error {
  readonly issues: ResearchReviewIssue[]

  constructor(issues: ResearchReviewIssue[]) {
    super(issues.map((i) => i.message).join(' '))
    this.issues = issues
  }
}

const unique = (values: string[]) => [...new Set(values)]

/**
 * Builds the simulated decision, its audit event (references only), and the updated
 * request. An approval names what it authorizes, both as structured data and as
 * conditions a reader can check.
 */
export function recordResearchReview(
  context: ResearchReviewContext,
  draft: ResearchReviewDraft,
  reviewer: PersonInfo | undefined,
  sequence: number,
): RecordedResearchReview {
  const issues = validateResearchReview(context, draft, reviewer)
  if (issues.length > 0 || !reviewer || draft.outcome === null || !context.project) {
    throw new InvalidResearchReview(issues)
  }
  const { request, project, now } = context
  const approved = draft.outcome === 'approved'
  // Keep the request's order, so the decision reads like the request.
  const organizations = project.participatingOrganizationIds.filter((id) => draft.approvedOrganizationIds.includes(id))
  const variables = project.variables.filter((v) => draft.approvedVariables.includes(v))
  const name = (id: string) => context.organization(id)?.shortName ?? id
  const conditions = approved
    ? [
        'Exécution compute-to-data uniquement ; aucune donnée individuelle en sortie.',
        `Effectif minimal de ${draft.minimumCellSize} par cellule.`,
        `Établissements autorisés : ${organizations.map(name).join(', ')}.`,
        `Variables autorisées : ${variables.join(', ')}.`,
        ...draft.conditions.map((c) => c.trim()).filter((c) => c.length > 0),
      ]
    : []
  const decision: GovernanceDecision = {
    id: `dec-sim-${request.id}-${sequence}`,
    subjectType: 'research_access_request',
    subjectId: request.id,
    outcome: draft.outcome,
    decidedById: reviewer.id,
    decidedAt: now.toISOString(),
    rationale: draft.rationale.trim(),
    conditions,
    validUntil: approved ? validUntil(now, draft.validityMonths).toISOString() : null,
    simulated: true,
    ...(approved && {
      researchAuthorization: {
        approvedOrganizationIds: organizations,
        approvedVariables: variables,
        minimumCellSize: draft.minimumCellSize,
      },
    }),
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
      organizationIds: unique([
        'org-governance',
        project.organizationId,
        ...(approved ? organizations : project.participatingOrganizationIds),
      ]),
      simulated: true,
    },
    request: { ...request, status: draft.outcome, decisionId: decision.id },
  }
}
