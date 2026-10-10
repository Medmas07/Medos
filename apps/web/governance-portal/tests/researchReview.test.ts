import { afterEach, describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'
import {
  InvalidResearchReview,
  MAX_VALIDITY_MONTHS,
  MINIMUM_CELL_SIZE_FLOOR,
  eligibleOrganizationIds,
  initialResearchDraft,
  recordResearchReview,
  researchChecks,
  validUntil,
  validateResearchReview,
  type ResearchReviewContext,
  type ResearchReviewDraft,
} from '../src/services/researchReview'
import { reviewStore } from '../src/services/reviewStore'
import type { ResearchAccessRequest, ResearchProject } from '../src/types/governance'

const DEMO_NOW = new Date('2026-10-10T10:00:00+01:00')
const reviewer = governanceService.getPerson('usr-olfa')

function request(id: string): ResearchAccessRequest {
  const found = governanceService.getResearchAccessRequests().find((r) => r.id === id)
  if (!found) throw new Error(`missing fixture ${id}`)
  return found
}

function context(
  projectChanges: Partial<ResearchProject> = {},
  requestId = 'rar-002',
): ResearchReviewContext {
  const req = request(requestId)
  const project = governanceService.getResearchProject(req.projectId)
  return {
    request: req,
    project: project && { ...project, ...projectChanges },
    organization: (id) => governanceService.getOrganization(id),
    now: DEMO_NOW,
  }
}

const approve = (ctx: ResearchReviewContext, changes: Partial<ResearchReviewDraft> = {}): ResearchReviewDraft => ({
  ...initialResearchDraft(ctx),
  outcome: 'approved',
  rationale: 'Protocole conforme, finalité de santé publique, exécution compute-to-data.',
  ...changes,
})

const reject = (ctx: ResearchReviewContext): ResearchReviewDraft => ({
  ...initialResearchDraft(ctx),
  outcome: 'rejected',
  rationale: 'Le protocole ne justifie pas les variables demandées.',
})

const fields = (ctx: ResearchReviewContext, draft: ResearchReviewDraft, person = reviewer) =>
  validateResearchReview(ctx, draft, person).map((i) => i.field)

const states = (ctx: ResearchReviewContext) => Object.fromEntries(researchChecks(ctx).map((c) => [c.id, c.state]))

afterEach(() => reviewStore.reset())

describe('Research access review checks (HC-078)', () => {
  it('passes every check for rar-002 (proj-002, asthma seasonality)', () => {
    expect(states(context())).toEqual({ project: 'pass', protocol: 'pass', scope: 'pass', organizations: 'pass' })
  })

  it('fails without a protocol, a population, or variables', () => {
    expect(states(context({ protocolDocument: null })).protocol).toBe('fail')
    expect(states(context({ population: '  ' })).scope).toBe('fail')
    expect(states(context({ variables: [] })).scope).toBe('fail')
  })

  it('fails when the request matches no known project', () => {
    const ctx = { ...context(), project: undefined }

    expect(states(ctx).project).toBe('fail')
  })

  it('only lets data come from approved organizations with a node', () => {
    const ctx = context({ participatingOrganizationIds: ['org-hospital-b', 'org-hospital-c'] })

    expect(eligibleOrganizationIds(ctx)).toEqual(['org-hospital-b'])
    expect(researchChecks(ctx).find((c) => c.id === 'organizations')?.detail).toContain('exclu')
    expect(states(context({ participatingOrganizationIds: ['org-hospital-c'] })).organizations).toBe('fail')
  })

  it('starts from the whole eligible request, 12 months, and a cell size of 10', () => {
    expect(initialResearchDraft(context())).toMatchObject({
      approvedOrganizationIds: ['org-hospital-b', 'org-private-practice'],
      approvedVariables: ['Mois de consultation', "Tranche d'âge", 'Passage aux urgences'],
      validityMonths: MAX_VALIDITY_MONTHS,
      minimumCellSize: MINIMUM_CELL_SIZE_FLOOR,
    })
  })
})

describe('Research access review rules (HC-078)', () => {
  it('accepts a complete approval and a complete rejection', () => {
    const ctx = context()

    expect(fields(ctx, approve(ctx))).toEqual([])
    expect(fields(ctx, reject(ctx))).toEqual([])
  })

  it('reports every missing part of an empty draft', () => {
    const ctx = context()

    expect(fields(ctx, initialResearchDraft(ctx))).toEqual(['outcome', 'rationale'])
  })

  it('blocks approval when a check fails, but always allows a motivated rejection', () => {
    const ctx = context({ protocolDocument: null })

    expect(fields(ctx, approve(ctx))).toContain('checks')
    expect(fields(ctx, reject(ctx))).toEqual([])
  })

  it('lets an approval only narrow the request', () => {
    const ctx = context()

    expect(fields(ctx, approve(ctx, { approvedOrganizationIds: [] }))).toEqual(['organizations'])
    expect(fields(ctx, approve(ctx, { approvedOrganizationIds: ['org-hospital-a'] }))).toEqual(['organizations'])
    expect(fields(ctx, approve(ctx, { approvedVariables: [] }))).toEqual(['variables'])
    expect(fields(ctx, approve(ctx, { approvedVariables: ['Diagnostic détaillé'] }))).toEqual(['variables'])
    expect(fields(ctx, approve(ctx, { approvedVariables: ['Mois de consultation'] }))).toEqual([])
  })

  it.each([0, 13, 1.5, Number.NaN])('rejects a validity of %s months', (months) => {
    const ctx = context()

    expect(fields(ctx, approve(ctx, { validityMonths: months }))).toEqual(['validity'])
  })

  it.each([9, 10.5, Number.NaN])('rejects a minimum cell size of %s', (size) => {
    const ctx = context()

    expect(fields(ctx, approve(ctx, { minimumCellSize: size }))).toEqual(['cellSize'])
  })

  it('accepts a stricter minimum cell size', () => {
    const ctx = context()

    expect(fields(ctx, approve(ctx, { minimumCellSize: 20 }))).toEqual([])
  })

  it('lets no one from the research team or a participating organization decide', () => {
    const ctx = context()

    expect(fields(ctx, approve(ctx), { ...reviewer!, organizationId: 'org-research-lab' })).toEqual(['reviewer'])
    expect(fields(ctx, approve(ctx), { ...reviewer!, organizationId: 'org-hospital-b' })).toEqual(['reviewer'])
    expect(fields(ctx, approve(ctx), { ...reviewer!, id: 'usr-aymen' })).toEqual(['reviewer'])
    expect(fields(ctx, approve(ctx), governanceService.getPerson('usr-aymen'))).toContain('reviewer')
  })

  it('refuses a second decision on a request already decided', () => {
    const ctx = context({}, 'rar-001')

    expect(fields(ctx, reject(ctx))).toContain('request')
  })
})

describe('Recording a simulated research decision (HC-078)', () => {
  it('records exactly what an approval authorizes', () => {
    const ctx = context()
    const draft = approve(ctx, {
      approvedOrganizationIds: ['org-hospital-b'],
      approvedVariables: ['Passage aux urgences', 'Mois de consultation'],
      validityMonths: 6,
      minimumCellSize: 15,
      conditions: ['  Publication après relecture par l’Autorité.  ', ''],
    })

    const { decision, auditEvent, request: updated } = recordResearchReview(ctx, draft, reviewer, 1)

    expect(decision).toMatchObject({
      id: 'dec-sim-rar-002-1',
      subjectType: 'research_access_request',
      subjectId: 'rar-002',
      outcome: 'approved',
      decidedById: 'usr-olfa',
      decidedAt: DEMO_NOW.toISOString(),
      validUntil: validUntil(DEMO_NOW, 6).toISOString(),
      simulated: true,
      researchAuthorization: {
        approvedOrganizationIds: ['org-hospital-b'],
        // In the request's order, not the reviewer's clicks.
        approvedVariables: ['Mois de consultation', 'Passage aux urgences'],
        minimumCellSize: 15,
      },
    })
    expect(decision.conditions).toEqual([
      'Exécution compute-to-data uniquement ; aucune donnée individuelle en sortie.',
      'Effectif minimal de 15 par cellule.',
      'Établissements autorisés : HR Oued Zitoun.',
      'Variables autorisées : Mois de consultation, Passage aux urgences.',
      'Publication après relecture par l’Autorité.',
    ])
    expect(auditEvent).toEqual({
      id: 'evt-sim-1',
      at: DEMO_NOW.toISOString(),
      actorId: 'usr-olfa',
      action: 'decision_recorded',
      subjectType: 'decision',
      subjectId: 'dec-sim-rar-002-1',
      organizationIds: ['org-governance', 'org-research-lab', 'org-hospital-b'],
      simulated: true,
    })
    expect(updated).toMatchObject({ status: 'approved', decisionId: 'dec-sim-rar-002-1' })
  })

  it('ends a 6-month authorization six calendar months later', () => {
    expect(validUntil(DEMO_NOW, 6).toISOString()).toBe('2027-04-10T09:00:00.000Z')
  })

  it('records a rejection with no authorization, validity, or conditions', () => {
    const ctx = context()

    const { decision, request: updated } = recordResearchReview(ctx, reject(ctx), reviewer, 1)

    expect(decision.researchAuthorization).toBeUndefined()
    expect(decision.validUntil).toBeNull()
    expect(decision.conditions).toEqual([])
    expect(updated.status).toBe('rejected')
  })

  it('refuses an invalid decision', () => {
    const ctx = context()

    expect(() => recordResearchReview(ctx, initialResearchDraft(ctx), reviewer, 1)).toThrow(InvalidResearchReview)
  })

  it('shows the decision across the portal, then returns to the fixtures on reset', () => {
    const ctx = context()
    const before = governanceService.getDashboardMetrics()

    reviewStore.recordResearch(recordResearchReview(ctx, approve(ctx), reviewer, reviewStore.nextSequence()))

    expect(request('rar-002').status).toBe('approved')
    const after = governanceService.getDashboardMetrics()
    expect(after.underReviewResearch).toBe(before.underReviewResearch - 1)
    expect(after.approvedResearch).toBe(before.approvedResearch + 1)

    reviewStore.reset()

    expect(request('rar-002').status).toBe('under_review')
    expect(governanceService.getDecision('dec-sim-rar-002-1')).toBeUndefined()
  })
})
