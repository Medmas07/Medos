import { describe, expect, it } from 'vitest'
import { submitAccessRequest } from '../src/services/projectAccessRequest'
import { createResearchProject } from '../src/services/projectCreation'
import { applyDocumentUpload } from '../src/services/projectDocuments'
import { saveHospitals } from '../src/services/projectHospitals'
import { savePopulation } from '../src/services/projectPopulation'
import { saveVariables } from '../src/services/projectVariables'
import { deriveRequestTracking } from '../src/services/requestTracking'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot, type DemoScenario } from '../src/services/researchService'
import type { ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const load = (now = NOW, scenario: DemoScenario = 'nominal') =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now, scenario })

const tracked = (snapshot: ResearchSnapshot, requestId: string) =>
  deriveRequestTracking(snapshot).requests.find((r) => r.request.id === requestId)!

/** The nominal snapshot with `proj-003` created, completed, and submitted in this session as `rar-003`. */
async function withSessionRequest(): Promise<ResearchSnapshot> {
  let snapshot = (
    await createResearchProject(
      await load(),
      {
        title: 'Insuffisance rénale chronique et diabète',
        summary: "Décrire la fréquence de l'insuffisance rénale chronique chez les adultes diabétiques suivis.",
      },
      { delayMs: 0, now: NOW },
    )
  ).snapshot
  snapshot = applyDocumentUpload(snapshot, 'proj-003', 'protocol', {
    fileName: 'Protocole_IRC.pdf',
    sizeBytes: 120_000,
    mediaType: 'application/pdf',
    uploadedAt: NOW.toISOString(),
  })
  snapshot = await savePopulation(
    snapshot,
    'proj-003',
    { description: 'Adultes diabétiques suivis en consultation.', ageMin: '18', ageMax: '', encounterFrom: '', encounterTo: '' },
    { delayMs: 0 },
  )
  snapshot = await saveVariables(
    snapshot,
    'proj-003',
    { names: ['age_band', 'hba1c'], justification: "L'HbA1c par tranche d'âge décrit le contrôle glycémique." },
    { delayMs: 0 },
  )
  snapshot = await saveHospitals(snapshot, 'proj-003', { organizationIds: ['org-hospital-a'] }, { delayMs: 0 })
  return (await submitAccessRequest(snapshot, 'proj-003', { acknowledged: true }, { delayMs: 0, now: NOW })).snapshot
}

describe('Research request tracking (HC-098, MOCKED)', () => {
  it('tracks a request under review without anticipating the decision', async () => {
    const r = tracked(await load(), 'rar-002')
    expect(r).toMatchObject({ state: 'under_review', decision: null, authorization: null, decidedBy: null, transmitted: true })
    expect(r.steps).toEqual([
      { id: 'submitted', state: 'done', at: '2026-10-02T16:30:00+01:00' },
      { id: 'review', state: 'current', at: null },
      { id: 'decision', state: 'upcoming', at: null },
    ])
  })

  it('shows an approval with its reviewer, conditions, and validity', async () => {
    const r = tracked(await load(), 'rar-001')
    expect(r.state).toBe('approved')
    expect(r.decision).toMatchObject({ id: 'dec-rar-001', outcome: 'approved' })
    expect(r.decision?.conditions).toHaveLength(2)
    expect(r.decidedBy).toMatchObject({ id: 'usr-olfa', role: 'governance_reviewer' })
    expect(r.authorization).toMatchObject({ state: 'valid', daysLeft: 283 })
    expect(r.steps.map((s) => [s.id, s.state, s.at])).toEqual([
      ['submitted', 'done', '2026-07-01T10:00:00+01:00'],
      ['review', 'done', null],
      ['decision', 'done', '2026-07-20T15:00:00+01:00'],
    ])
  })

  it('warns before an approval ends and blocks it once expired', async () => {
    expect(tracked(await load(new Date('2027-07-01T12:00:00+01:00')), 'rar-001').state).toBe('expiring')
    const expired = tracked(await load(new Date('2027-08-01T12:00:00+01:00')), 'rar-001')
    expect(expired.state).toBe('expired')
    expect(expired.steps.at(-1)).toMatchObject({ id: 'decision', state: 'blocked' })
  })

  it('shows a refusal first, with its blocked decision step', async () => {
    const snapshot = await load()
    const projects = snapshot.projects.map((s) =>
      s.request?.id === 'rar-002'
        ? {
            ...s,
            request: { ...s.request, status: 'rejected' as const, decisionId: 'dec-test' },
            decision: {
              id: 'dec-test',
              subjectType: 'research_access_request',
              subjectId: 'rar-002',
              outcome: 'rejected' as const,
              decidedById: 'usr-olfa',
              decidedAt: '2026-10-08T09:00:00+01:00',
              rationale: 'Justification des variables insuffisante.',
              conditions: [],
              validUntil: null,
            },
          }
        : s,
    )
    const tracking = deriveRequestTracking({ ...snapshot, projects })
    expect(tracking.requests.map((r) => [r.request.id, r.state])).toEqual([
      ['rar-002', 'rejected'],
      ['rar-001', 'approved'],
    ])
    expect(tracking.requests[0].authorization).toBeNull()
    expect(tracking.requests[0].steps.at(-1)).toEqual({ id: 'decision', state: 'blocked', at: '2026-10-08T09:00:00+01:00' })
  })

  it('orders requests under review before approvals and counts them by state', async () => {
    const tracking = deriveRequestTracking(await load())
    expect(tracking.requests.map((r) => r.request.id)).toEqual(['rar-002', 'rar-001'])
    expect(tracking.counts).toEqual({ under_review: 1, approved: 1, expiring: 0, expired: 0, rejected: 0 })
    expect(tracking.unsubmitted).toEqual([])
  })

  it('flags a request submitted in this session as not transmitted, still under review', async () => {
    const tracking = deriveRequestTracking(await withSessionRequest())
    expect(tracking.requests.map((r) => [r.request.id, r.state, r.transmitted])).toEqual([
      ['rar-003', 'under_review', false],
      ['rar-002', 'under_review', true],
      ['rar-001', 'approved', true],
    ])
    expect(tracking.counts.under_review).toBe(2)
  })

  it('lists drafts without a request, and nothing in the empty scenario', async () => {
    const snapshot = (
      await createResearchProject(
        await load(),
        { title: 'Projet sans demande encore', summary: "Un objectif scientifique assez long pour être valide ici." },
        { delayMs: 0, now: NOW },
      )
    ).snapshot
    expect(deriveRequestTracking(snapshot).unsubmitted.map((s) => s.project.id)).toEqual(['proj-003'])

    const empty = deriveRequestTracking(await load(NOW, 'empty'))
    expect(empty.requests).toEqual([])
    expect(empty.unsubmitted).toEqual([])
  })
})
