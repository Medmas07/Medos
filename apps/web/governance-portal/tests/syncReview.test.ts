import { afterEach, describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'
import { reviewStore } from '../src/services/reviewStore'
import { syncListRows } from '../src/services/syncRequestList'
import {
  InvalidSyncReview,
  initialSyncDraft,
  maxApprovedDays,
  recordSyncReview,
  syncChecks,
  validateSyncReview,
  type SyncReviewContext,
  type SyncReviewDraft,
} from '../src/services/syncReview'
import type { SynchronizationRequest } from '../src/types/governance'

// The demo dataset's reference date; grant-a-drx expires on 2026-10-24 at 09:00.
const DEMO_NOW = new Date('2026-10-10T10:00:00+01:00')
const DAY_MS = 24 * 60 * 60 * 1000
const reviewer = governanceService.getPerson('usr-olfa')

function request(id: string): SynchronizationRequest {
  const found = governanceService.getSynchronizationRequests().find((r) => r.id === id)
  if (!found) throw new Error(`missing fixture ${id}`)
  return found
}

function context(changes: Partial<SynchronizationRequest> = {}, now = DEMO_NOW): SyncReviewContext {
  const req = { ...request('sync-001'), ...changes }
  return {
    request: req,
    requester: governanceService.getOrganization(req.requesterOrganizationId),
    target: governanceService.getOrganization(req.targetOrganizationId),
    grant: governanceService.getAccessGrant(req.consent.accessGrantId),
    now,
  }
}

const approve = (ctx: SyncReviewContext, changes: Partial<SyncReviewDraft> = {}): SyncReviewDraft => ({
  ...initialSyncDraft(ctx),
  outcome: 'approved',
  rationale: 'Finalité de soins justifiée et autorisation de la patiente active.',
  conditions: ['  Aucune réutilisation à des fins de recherche.  ', ''],
  ...changes,
})

const reject = (ctx: SyncReviewContext): SyncReviewDraft => ({
  ...initialSyncDraft(ctx),
  outcome: 'rejected',
  rationale: 'Base d’autorisation insuffisante pour cette finalité.',
})

const fields = (ctx: SyncReviewContext, draft: SyncReviewDraft, person = reviewer) =>
  validateSyncReview(ctx, draft, person).map((i) => i.field)

const states = (ctx: SyncReviewContext) => Object.fromEntries(syncChecks(ctx).map((c) => [c.id, c.state]))

afterEach(() => reviewStore.reset())

describe('Synchronization review checks (HC-076)', () => {
  it('passes every check for sync-001 under Patient A’s active grant', () => {
    expect(states(context())).toEqual({ organizations: 'pass', consent: 'pass', duration: 'pass' })
  })

  it('never authorizes beyond the patient grant: 30 days requested, 13 possible', () => {
    const ctx = context()

    expect(maxApprovedDays(ctx)).toBe(13)
    expect(initialSyncDraft(ctx).approvedDays).toBe(13)
    expect(syncChecks(ctx).find((c) => c.id === 'duration')?.detail).toContain('limités à 13 jours')
  })

  it('keeps the requested duration when the grant outlasts it', () => {
    expect(maxApprovedDays(context({ durationDays: 7 }))).toBe(7)
  })

  it('fails the consent and duration checks once the grant has expired', () => {
    const afterGrant = context({}, new Date('2026-10-25T10:00:00+01:00'))

    expect(states(afterGrant)).toMatchObject({ consent: 'fail', duration: 'fail' })
    expect(maxApprovedDays(afterGrant)).toBe(0)
  })

  it('fails consent without any authorization basis', () => {
    expect(states(context({ consent: { basis: 'none', accessGrantId: null } })).consent).toBe('fail')
  })

  it('fails consent when the grant is for another patient, revoked, or narrower than the scope', () => {
    expect(states(context({ patientId: 'pat-b' })).consent).toBe('fail')
    expect(states(context({ consent: { basis: 'patient_grant', accessGrantId: 'grant-c-ines' } })).consent).toBe('fail')
    expect(states(context({ consent: { basis: 'patient_grant', accessGrantId: 'grant-unknown' } })).consent).toBe('fail')
    expect(states(context({ scope: ['medications', 'imaging'] })).consent).toBe('fail')
  })

  it('asks the reviewer to verify a signed consent form outside the portal', () => {
    expect(states(context({ consent: { basis: 'signed_consent_form', accessGrantId: null } })).consent).toBe('manual')
  })

  it('fails when an organization is not approved by the Authority', () => {
    expect(states(context({ targetOrganizationId: 'org-hospital-c' })).organizations).toBe('fail')
    expect(states(context({ targetOrganizationId: 'org-hospital-a' })).organizations).toBe('fail')
  })
})

describe('Synchronization review rules (HC-076)', () => {
  it('accepts a complete approval and a complete rejection', () => {
    const ctx = context()

    expect(fields(ctx, approve(ctx))).toEqual([])
    expect(fields(ctx, reject(ctx))).toEqual([])
  })

  it('reports every missing part of an empty draft', () => {
    const ctx = context()

    expect(fields(ctx, initialSyncDraft(ctx))).toEqual(['outcome', 'rationale'])
  })

  it('blocks approval when a check fails, but always allows a motivated refusal', () => {
    const ctx = context({ consent: { basis: 'none', accessGrantId: null } })

    expect(fields(ctx, approve(ctx))).toContain('checks')
    expect(fields(ctx, reject(ctx))).toEqual([])
  })

  it('requires the reviewer to confirm what the portal cannot verify', () => {
    const ctx = context({ consent: { basis: 'signed_consent_form', accessGrantId: null } })

    expect(fields(ctx, approve(ctx))).toEqual(['manual'])
    expect(fields(ctx, approve(ctx, { manualChecksConfirmed: true }))).toEqual([])
  })

  it.each([0, 14, 2.5, Number.NaN])('rejects an authorized duration of %s days', (days) => {
    const ctx = context()

    expect(fields(ctx, approve(ctx, { approvedDays: days }))).toEqual(['duration'])
  })

  it('lets no one from the requesting or target organization decide', () => {
    const ctx = context()
    const fromTarget = { ...reviewer!, organizationId: 'org-hospital-b' }
    const fromRequester = { ...reviewer!, organizationId: 'org-hospital-a' }

    expect(fields(ctx, approve(ctx), fromTarget)).toEqual(['reviewer'])
    expect(fields(ctx, approve(ctx), fromRequester)).toEqual(['reviewer'])
    expect(fields(ctx, approve(ctx), governanceService.getPerson('usr-mehdi'))).toContain('reviewer')
  })

  it('refuses a second decision on a request already decided', () => {
    const ctx = { ...context(), request: request('sync-002') }

    expect(fields(ctx, reject(ctx))).toContain('request')
  })
})

describe('Recording a simulated synchronization decision (HC-076)', () => {
  it('builds a temporary authorization limited by the patient grant', () => {
    const ctx = context()

    const { decision, auditEvent, request: updated } = recordSyncReview(ctx, approve(ctx), reviewer, 1)

    expect(decision).toMatchObject({
      id: 'dec-sim-sync-001-1',
      subjectType: 'synchronization_request',
      subjectId: 'sync-001',
      outcome: 'approved',
      decidedById: 'usr-olfa',
      decidedAt: DEMO_NOW.toISOString(),
      validUntil: new Date(DEMO_NOW.getTime() + 13 * DAY_MS).toISOString(),
      simulated: true,
    })
    expect(new Date(decision.validUntil!) < new Date('2026-10-24T09:00:00+01:00')).toBe(true)
    expect(decision.conditions).toEqual([
      'Durée autorisée : 13 jours (demandée : 30 jours).',
      'Aucune réutilisation à des fins de recherche.',
    ])
    expect(auditEvent).toEqual({
      id: 'evt-sim-1',
      at: DEMO_NOW.toISOString(),
      actorId: 'usr-olfa',
      action: 'decision_recorded',
      subjectType: 'decision',
      subjectId: 'dec-sim-sync-001-1',
      organizationIds: ['org-governance', 'org-hospital-a', 'org-hospital-b'],
      simulated: true,
    })
    expect(updated).toMatchObject({ status: 'approved', decisionId: 'dec-sim-sync-001-1' })
  })

  it('records a refusal with no validity and no conditions', () => {
    const ctx = context()

    const { decision, request: updated } = recordSyncReview(
      ctx,
      { ...reject(ctx), conditions: ['ignorée'] },
      reviewer,
      1,
    )

    expect((({ validUntil, conditions }) => ({ validUntil, conditions }))(decision)).toEqual({
      validUntil: null,
      conditions: [],
    })
    expect(updated.status).toBe('rejected')
  })

  it('refuses an invalid decision', () => {
    const ctx = context()

    expect(() => recordSyncReview(ctx, initialSyncDraft(ctx), reviewer, 1)).toThrow(InvalidSyncReview)
  })

  it('shows the decision across the portal, then returns to the fixtures on reset', () => {
    const ctx = context()
    const before = governanceService.getDashboardMetrics()

    reviewStore.recordSync(recordSyncReview(ctx, approve(ctx), reviewer, reviewStore.nextSequence()))

    expect(request('sync-001').status).toBe('approved')
    expect(governanceService.getDashboardMetrics().pendingSyncs).toBe(before.pendingSyncs - 1)
    const row = syncListRows(
      governanceService.getSynchronizationRequests(),
      (id) => governanceService.getDecision(id),
      DEMO_NOW,
    ).find((r) => r.request.id === 'sync-001')
    expect(row?.status).toBe('active')

    reviewStore.reset()

    expect(request('sync-001').status).toBe('pending')
    expect(governanceService.getDecision('dec-sim-sync-001-1')).toBeUndefined()
  })
})
