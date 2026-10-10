import { afterEach, describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'
import {
  InvalidReview,
  emptyDraft,
  recordReview,
  reviewFindings,
  validateReview,
  type ReviewDraft,
} from '../src/services/hospitalReview'
import { reviewStore } from '../src/services/reviewStore'
import type { HospitalApplication } from '../src/types/governance'

const AT = new Date('2026-10-10T10:30:00+01:00')
const reviewer = governanceService.getPerson('usr-olfa')

function application(id: string): HospitalApplication {
  const app = governanceService.getHospitalApplications().find((a) => a.id === id)
  if (!app) throw new Error(`missing fixture ${id}`)
  return app
}

const hospitalC = () => application('app-hospital-c')

const approval: ReviewDraft = {
  outcome: 'approved',
  rationale: 'Dossier conforme sous réserve de l’attestation d’assurance.',
  conditions: ['  Fournir l’attestation d’assurance avant la mise en service.  ', ''],
  findingsAcknowledged: true,
}

const rejection: ReviewDraft = {
  outcome: 'rejected',
  rationale: 'Pièces obligatoires manquantes et incohérences techniques.',
  conditions: ['ignorée pour un rejet'],
  findingsAcknowledged: true,
}

function fields(draft: ReviewDraft, app = hospitalC(), person = reviewer) {
  return validateReview(app, draft, person).map((i) => i.field)
}

afterEach(() => reviewStore.reset())

describe('Hospital approval review rules (HC-073)', () => {
  it('lists every finding the reviewer must examine for Hospital C', () => {
    const findings = reviewFindings(hospitalC())

    expect(findings.missingDocuments.map((d) => d.id)).toEqual(['doc-c-assurance'])
    expect(findings.unacceptedAgreements).toEqual([])
    expect(findings.completenessFindings).toEqual(["Attestation d'assurance manquante."])
    expect(findings.advisoryFindings).toHaveLength(2)
  })

  it('accepts a complete approval and a complete rejection', () => {
    expect(fields(approval)).toEqual([])
    expect(fields(rejection)).toEqual([])
  })

  it('reports every missing part of an empty draft', () => {
    expect(fields(emptyDraft)).toEqual(['outcome', 'rationale', 'acknowledgement'])
  })

  it('requires the reviewer to acknowledge the findings, including the advisory AI ones', () => {
    expect(fields({ ...approval, findingsAcknowledged: false })).toEqual(['acknowledgement'])
  })

  it('requires a substantive rationale', () => {
    expect(fields({ ...approval, rationale: '   Conforme.   ' })).toEqual(['rationale'])
  })

  it('requires a condition to approve an incomplete application, but not to reject it', () => {
    expect(fields({ ...approval, conditions: ['   ', ''] })).toEqual(['conditions'])
    expect(fields({ ...rejection, conditions: [] })).toEqual([])
  })

  it('lets only a governance reviewer decide', () => {
    const manager = governanceService.getPerson('usr-mehdi')

    expect(fields(approval, hospitalC(), manager)).toContain('reviewer')
    const nobody = validateReview(hospitalC(), approval, undefined).map((i) => i.field)
    expect(nobody).toContain('reviewer')
  })

  it('never lets the applicant organization decide on its own application', () => {
    const insider = { ...reviewer!, organizationId: 'org-hospital-c' }

    expect(fields(approval, hospitalC(), insider)).toEqual(['reviewer'])
  })

  it('refuses a second decision on an application already decided', () => {
    expect(fields(approval, application('app-hospital-a'))).toContain('application')
  })
})

describe('Recording a simulated decision (HC-073)', () => {
  it('builds a simulated approval, its audit event, and the updated application', () => {
    const recorded = recordReview(hospitalC(), approval, reviewer, AT, 1)

    expect(recorded.decision).toEqual({
      id: 'dec-sim-hospital-c-1',
      subjectType: 'hospital_application',
      subjectId: 'app-hospital-c',
      outcome: 'approved',
      decidedById: 'usr-olfa',
      decidedAt: AT.toISOString(),
      rationale: approval.rationale,
      conditions: ['Fournir l’attestation d’assurance avant la mise en service.'],
      validUntil: null,
      simulated: true,
    })
    expect(recorded.application.status).toBe('approved')
    expect(recorded.application.decisionId).toBe('dec-sim-hospital-c-1')
    const humanStep = recorded.application.reviewSteps.find((s) => s.step === 'human_review')
    expect(humanStep).toMatchObject({ status: 'completed', reviewerId: 'usr-olfa' })
  })

  it('keeps the audit event to references only', () => {
    const { auditEvent } = recordReview(hospitalC(), approval, reviewer, AT, 1)

    expect(auditEvent).toEqual({
      id: 'evt-sim-1',
      at: AT.toISOString(),
      actorId: 'usr-olfa',
      action: 'decision_recorded',
      subjectType: 'decision',
      subjectId: 'dec-sim-hospital-c-1',
      organizationIds: ['org-governance', 'org-hospital-c'],
      simulated: true,
    })
  })

  it('drops conditions from a rejection', () => {
    const { decision, application: updated } = recordReview(hospitalC(), rejection, reviewer, AT, 1)

    expect(decision.outcome).toBe('rejected')
    expect(decision.conditions).toEqual([])
    expect(updated.status).toBe('rejected')
  })

  it('refuses an invalid decision', () => {
    expect(() => recordReview(hospitalC(), emptyDraft, reviewer, AT, 1)).toThrow(InvalidReview)
  })
})

describe('Simulated decisions in the portal state (HC-073)', () => {
  it('shows a recorded decision across the portal without changing the fixtures', () => {
    const before = governanceService.getDashboardMetrics()

    reviewStore.record(recordReview(hospitalC(), approval, reviewer, AT, reviewStore.nextSequence()))

    expect(application('app-hospital-c').status).toBe('approved')
    expect(governanceService.getDecision('dec-sim-hospital-c-1')?.simulated).toBe(true)
    expect(governanceService.getAuditEvents().at(-1)?.id).toBe('evt-sim-1')
    expect(governanceService.getProofForEvent('evt-sim-1')).toBeUndefined()
    const after = governanceService.getDashboardMetrics()
    expect(after.pendingApplications).toBe(before.pendingApplications - 1)
    expect(after.approvedHospitals).toBe(before.approvedHospitals + 1)
  })

  it('returns to the canonical fixtures on reset', () => {
    reviewStore.record(recordReview(hospitalC(), rejection, reviewer, AT, reviewStore.nextSequence()))

    reviewStore.reset()

    expect(application('app-hospital-c').status).toBe('human_review')
    expect(governanceService.getDecision('dec-sim-hospital-c-1')).toBeUndefined()
    expect(governanceService.getAuditEvents().some((e) => e.simulated)).toBe(false)
  })

  it('notifies subscribers when a decision is recorded', () => {
    let calls = 0
    const unsubscribe = reviewStore.subscribe(() => calls++)

    reviewStore.record(recordReview(hospitalC(), approval, reviewer, AT, 1))
    unsubscribe()
    reviewStore.reset()

    expect(calls).toBe(1)
  })
})
