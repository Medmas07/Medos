import { describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'
import {
  countResearchRows,
  filterResearchRows,
  researchListRows,
  researchListStatus,
  RESEARCH_FILTER_LABELS,
  RESEARCH_STATUS_LABELS,
} from '../src/services/researchRequestList'
import type { GovernanceDecision, ResearchAccessRequest } from '../src/types/governance'

// The demo dataset's reference date.
const DEMO_NOW = new Date('2026-10-10T10:00:00+01:00')

const demoRows = (now = DEMO_NOW) =>
  researchListRows(
    governanceService.getResearchAccessRequests(),
    (projectId) => governanceService.getResearchProject(projectId),
    (decisionId) => governanceService.getDecision(decisionId),
    now,
  )

const request = (changes: Partial<ResearchAccessRequest>): ResearchAccessRequest => ({
  ...governanceService.getResearchAccessRequests()[0],
  ...changes,
})

const decision = (validUntil: string | null): GovernanceDecision => ({
  id: 'dec-test-rar',
  subjectType: 'research_access_request',
  subjectId: 'rar-test',
  outcome: 'approved',
  decidedById: 'usr-olfa',
  decidedAt: '2026-07-20T15:00:00+01:00',
  rationale: 'Protocole conforme sous Compute-to-Data.',
  conditions: ['Aucune donnée brute en sortie.'],
  validUntil,
})

describe('Research access request list (HC-077)', () => {
  it('lists every demo research request, under_review first, with its status today', () => {
    expect(demoRows().map((r) => [r.request.id, r.status])).toEqual([
      ['rar-002', 'under_review'],
      ['rar-001', 'active'],
    ])
  })

  it('resolves associated research project details and participating hospitals', () => {
    const rows = demoRows()
    const row001 = rows.find((r) => r.request.id === 'rar-001')
    expect(row001).toBeDefined()
    expect(row001?.project?.title).toContain('Facteurs de risque cardiométaboliques')
    expect(row001?.project?.participatingOrganizationIds).toEqual(['org-hospital-a', 'org-hospital-b'])

    const row002 = rows.find((r) => r.request.id === 'rar-002')
    expect(row002).toBeDefined()
    expect(row002?.project?.title).toContain('Asthme de l\'adulte jeune')
    expect(row002?.project?.participatingOrganizationIds).toEqual(['org-hospital-b', 'org-private-practice'])
  })

  it('shows an approved research request as expired once its decision has lapsed', () => {
    const approved = request({ status: 'approved' })

    expect(researchListStatus(approved, decision('2026-08-01T00:00:00+01:00'), DEMO_NOW)).toBe('expired')
    expect(researchListStatus(approved, decision('2027-07-20T15:00:00+01:00'), DEMO_NOW)).toBe('active')
    expect(researchListStatus(approved, decision(null), DEMO_NOW)).toBe('active')
  })

  it('treats the expiry instant itself as expired', () => {
    const until = '2026-09-01T00:00:00+01:00'
    expect(researchListStatus(request({ status: 'approved' }), decision(until), new Date(until))).toBe('expired')
  })

  it('keeps rar-001 active while its authorization is valid', () => {
    const rar001 = demoRows().find((r) => r.request.id === 'rar-001')
    expect(rar001).toMatchObject({
      status: 'active',
      validUntil: '2027-07-20T15:00:00+01:00',
    })
  })

  it('carries a validity end only for approved requests', () => {
    expect(demoRows().map((r) => r.validUntil)).toEqual([null, '2027-07-20T15:00:00+01:00'])
  })

  it('orders research requests of the same status by newest submission', () => {
    const rows = researchListRows(
      [
        request({ id: 'rar-old', submittedAt: '2026-01-01T00:00:00+01:00', status: 'under_review' }),
        request({ id: 'rar-new', submittedAt: '2026-09-01T00:00:00+01:00', status: 'under_review' }),
      ],
      () => undefined,
      () => undefined,
      DEMO_NOW,
    )

    expect(rows.map((r) => r.request.id)).toEqual(['rar-new', 'rar-old'])
  })

  it('filters and counts research rows by status, including empty filters', () => {
    const rows = demoRows()

    expect(countResearchRows(rows)).toEqual({
      all: 2,
      under_review: 1,
      active: 1,
      expired: 0,
      rejected: 0,
    })

    expect(filterResearchRows(rows, 'under_review').map((r) => r.request.id)).toEqual(['rar-002'])
    expect(filterResearchRows(rows, 'active').map((r) => r.request.id)).toEqual(['rar-001'])
    expect(filterResearchRows(rows, 'expired')).toHaveLength(0)
    expect(filterResearchRows(rows, 'rejected')).toHaveLength(0)
    expect(filterResearchRows(rows, 'all')).toHaveLength(2)
  })

  it('provides human-readable status and filter labels for reviewers', () => {
    expect(RESEARCH_STATUS_LABELS.under_review).toBe('En examen')
    expect(RESEARCH_STATUS_LABELS.active).toBe('Autorisée')
    expect(RESEARCH_STATUS_LABELS.expired).toBe('Expirée')
    expect(RESEARCH_STATUS_LABELS.rejected).toBe('Rejetée')

    expect(RESEARCH_FILTER_LABELS.all).toBe('Toutes')
    expect(RESEARCH_FILTER_LABELS.under_review).toBe('En examen')
  })
})
