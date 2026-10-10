import { describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'
import {
  consentLabel,
  countSyncRows,
  filterSyncRows,
  scopeLabel,
  syncListRows,
  syncListStatus,
} from '../src/services/syncRequestList'
import type { GovernanceDecision, SynchronizationRequest } from '../src/types/governance'

// The demo dataset's reference date.
const DEMO_NOW = new Date('2026-10-10T10:00:00+01:00')

const demoRows = (now = DEMO_NOW) =>
  syncListRows(
    governanceService.getSynchronizationRequests(),
    (id) => governanceService.getDecision(id),
    now,
  )

const request = (changes: Partial<SynchronizationRequest>): SynchronizationRequest => ({
  ...governanceService.getSynchronizationRequests()[0],
  ...changes,
})

const decision = (validUntil: string | null): GovernanceDecision => ({
  id: 'dec-x',
  subjectType: 'synchronization_request',
  subjectId: 'sync-x',
  outcome: 'approved',
  decidedById: 'usr-olfa',
  decidedAt: '2026-01-01T00:00:00+01:00',
  rationale: 'Finalité de soins justifiée.',
  conditions: [],
  validUntil,
})

describe('Synchronization request list (HC-074)', () => {
  it('lists every demo request, pending first, with its status today', () => {
    expect(demoRows().map((r) => [r.request.id, r.status])).toEqual([
      ['sync-001', 'pending'],
      ['sync-002', 'expired'],
      ['sync-003', 'rejected'],
    ])
  })

  it('shows an approved request as expired once its decision has lapsed', () => {
    const approved = request({ status: 'approved' })

    expect(syncListStatus(approved, decision('2026-03-12T14:30:00+01:00'), DEMO_NOW)).toBe('expired')
    expect(syncListStatus(approved, decision('2026-12-31T00:00:00+01:00'), DEMO_NOW)).toBe('active')
    expect(syncListStatus(approved, decision(null), DEMO_NOW)).toBe('active')
  })

  it('treats the expiry instant itself as expired', () => {
    const until = '2026-03-12T14:30:00+01:00'

    expect(syncListStatus(request({ status: 'approved' }), decision(until), new Date(until))).toBe('expired')
  })

  it('keeps sync-002 active while its authorization was still valid', () => {
    const sync002 = demoRows(new Date('2026-01-10T10:00:00+01:00')).find(
      (r) => r.request.id === 'sync-002',
    )

    expect(sync002).toMatchObject({ status: 'active', validUntil: '2026-03-12T14:30:00+01:00' })
  })

  it('carries a validity end only for approved requests', () => {
    expect(demoRows().map((r) => r.validUntil)).toEqual([null, '2026-03-12T14:30:00+01:00', null])
  })

  it('orders requests of the same status by newest submission', () => {
    const rows = syncListRows(
      [
        request({ id: 'old', submittedAt: '2026-01-01T00:00:00+01:00' }),
        request({ id: 'new', submittedAt: '2026-09-01T00:00:00+01:00' }),
      ],
      () => undefined,
      DEMO_NOW,
    )

    expect(rows.map((r) => r.request.id)).toEqual(['new', 'old'])
  })

  it('filters and counts by status, including an empty filter', () => {
    const rows = demoRows()

    expect(countSyncRows(rows)).toEqual({ all: 3, pending: 1, active: 0, expired: 1, rejected: 1 })
    expect(filterSyncRows(rows, 'pending').map((r) => r.request.id)).toEqual(['sync-001'])
    expect(filterSyncRows(rows, 'active')).toEqual([])
    expect(filterSyncRows(rows, 'all')).toHaveLength(3)
  })

  it('labels scopes and consent bases for reviewers, without dropping unknown scopes', () => {
    expect(['encounters', 'medications', 'labReports'].map(scopeLabel)).toEqual([
      'Consultations',
      'Médicaments',
      'Analyses biologiques',
    ])
    expect(scopeLabel('imaging')).toBe('imaging')
    expect(consentLabel('none')).toBe('Aucune autorisation')
    expect(consentLabel('patient_grant')).toBe('Autorisation du patient')
  })
})
