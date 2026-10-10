import { afterEach, describe, expect, it } from 'vitest'
import {
  auditTimeline,
  countByDomain,
  filterTimeline,
  involvedOrganizationIds,
  timelineEntry,
  type AuditLookups,
} from '../src/services/auditTimeline'
import { governanceService } from '../src/services/governanceService'
import { recordReview } from '../src/services/hospitalReview'
import { reviewStore } from '../src/services/reviewStore'
import type { GovernanceAuditEvent } from '../src/types/governance'

const lookups: AuditLookups = {
  decision: (id) => governanceService.getDecision(id),
  proofForEvent: (id) => governanceService.getProofForEvent(id),
}

const timeline = () => auditTimeline(governanceService.getAuditEvents(), lookups)
const entry = (id: string) => timeline().find((e) => e.event.id === id)!

afterEach(() => reviewStore.reset())

describe('Governance audit timeline (HC-079)', () => {
  it('lists every governance event, newest first', () => {
    expect(timeline().map((e) => e.event.id)).toEqual([
      'evt-007',
      'evt-006',
      'evt-005',
      'evt-004',
      'evt-003',
      'evt-002',
      'evt-001',
    ])
  })

  it('says what each decision was about and how it ended', () => {
    expect(entry('evt-001')).toMatchObject({
      domain: 'hospital',
      title: 'Décision : adhésion approuvée',
      subjectRef: 'app-hospital-a',
      outcome: 'approved',
      tone: 'success',
    })
    expect(entry('evt-005')).toMatchObject({
      domain: 'synchronization',
      title: 'Décision : synchronisation rejetée',
      subjectRef: 'sync-003',
      outcome: 'rejected',
      tone: 'danger',
    })
    expect(entry('evt-004')).toMatchObject({
      domain: 'research',
      title: 'Décision : accès recherche approuvée',
      subjectRef: 'rar-001',
    })
  })

  it('names submissions and incoming requests', () => {
    expect(entry('evt-006')).toMatchObject({
      domain: 'hospital',
      title: 'Demande d’adhésion déposée',
      subjectRef: 'app-hospital-c',
      outcome: null,
      tone: 'info',
    })
    expect(entry('evt-007')).toMatchObject({
      domain: 'synchronization',
      title: 'Demande de synchronisation reçue',
      subjectRef: 'sync-001',
    })
  })

  it('links the anchored ledger proofs, and only those', () => {
    expect(timeline().filter((e) => e.proof).map((e) => [e.event.id, e.proof!.id])).toEqual([
      ['evt-004', 'proof-004'],
      ['evt-003', 'proof-003'],
    ])
  })

  it('still lists an event whose decision cannot be resolved', () => {
    const orphan: GovernanceAuditEvent = {
      id: 'evt-x',
      at: '2026-01-01T00:00:00+01:00',
      actorId: 'usr-olfa',
      action: 'decision_recorded',
      subjectType: 'decision',
      subjectId: 'dec-unknown',
      organizationIds: ['org-governance'],
    }

    expect(timelineEntry(orphan, lookups)).toMatchObject({
      domain: null,
      title: 'Décision enregistrée',
      subjectRef: 'dec-unknown',
      tone: 'neutral',
    })
  })

  it('orders events at the same instant by id, so the order never flickers', () => {
    const at = '2026-01-01T00:00:00+01:00'
    const events = ['evt-a', 'evt-b'].map((id) => ({ ...entry('evt-006').event, id, at }))

    expect(auditTimeline(events, lookups).map((e) => e.event.id)).toEqual(['evt-b', 'evt-a'])
  })

  it('filters by domain and by organization, and counts by domain', () => {
    const entries = timeline()

    expect(countByDomain(entries)).toEqual({ all: 7, hospital: 3, synchronization: 3, research: 1 })
    expect(filterTimeline(entries, { domain: 'research', organizationId: null }).map((e) => e.event.id)).toEqual(['evt-004'])
    expect(
      filterTimeline(entries, { domain: 'all', organizationId: 'org-private-practice' }).map((e) => e.event.id),
    ).toEqual(['evt-003'])
    expect(filterTimeline(entries, { domain: 'hospital', organizationId: 'org-research-lab' })).toEqual([])
  })

  it('offers only organizations that appear in the events', () => {
    expect(involvedOrganizationIds(timeline())).toEqual([
      'org-hospital-a',
      'org-hospital-b',
      'org-hospital-c',
      'org-governance',
      'org-research-lab',
      'org-private-practice',
    ])
  })

  it('shows a decision recorded in the session first, marked simulated and not anchored', () => {
    const app = governanceService.getHospitalApplications().find((a) => a.id === 'app-hospital-c')!
    reviewStore.record(
      recordReview(
        app,
        {
          outcome: 'rejected',
          rationale: 'Attestation d’assurance manquante et incohérences techniques.',
          conditions: [],
          findingsAcknowledged: true,
        },
        governanceService.getPerson('usr-olfa'),
        new Date('2026-10-10T11:00:00+01:00'),
        reviewStore.nextSequence(),
      ),
    )

    const [first] = timeline()
    expect(first).toMatchObject({
      domain: 'hospital',
      title: 'Décision : adhésion rejetée',
      subjectRef: 'app-hospital-c',
      simulated: true,
      proof: undefined,
    })
  })

  it('never carries patient identity, even for synchronization events', () => {
    const patients = ['pat-a', 'pat-b', 'pat-c', 'FED-PAT']

    for (const e of timeline()) {
      const text = JSON.stringify([e.title, e.subjectRef, e.event])
      for (const ref of patients) expect(text).not.toContain(ref)
    }
  })
})
