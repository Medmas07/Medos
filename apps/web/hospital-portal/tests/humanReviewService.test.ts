import { describe, expect, it } from 'vitest'
import { applyUpload, uploadDocument } from '../src/services/documentService'
import {
  applicationNotifications,
  humanReviewState,
  outstandingDocuments,
  refreshReviewState,
  supplementsSinceSubmission,
} from '../src/services/humanReviewService'
import { DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, loadOnboardingSnapshot, scenarioFromSearch } from '../src/services/onboardingService'
import { applyRegistration, demoRegistrationInput, submitRegistration } from '../src/services/registrationService'
import type { HospitalApplication } from '../src/types/onboarding'

const now = new Date('2026-10-10T16:00:00+01:00')
const load = (scenario: 'nominal' | 'empty' = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

describe('Human hospital validation state', () => {
  it('shows the Cap Azur review as pending with a reviewer assigned, without naming the reviewer', async () => {
    const { application } = await load()
    const state = humanReviewState(application)
    expect(state).toEqual({ kind: 'pending', reviewerAssigned: true, submittedAt: '2026-10-06T15:20:00+01:00' })
    expect(JSON.stringify(state)).not.toContain('usr-olfa')
  })

  it('reports no review before submission and none recorded for older applications', async () => {
    expect(humanReviewState(null)).toEqual({ kind: 'not_submitted' })
    const registered = await submitRegistration(demoRegistrationInput(), { delayMs: 0, now })
    if (registered.kind !== 'accepted') throw new Error('expected acceptance')
    const draft = applyRegistration(await load('empty'), demoRegistrationInput(), registered.receipt)
    expect(humanReviewState(draft.application)).toEqual({ kind: 'not_submitted' })

    const legacy: HospitalApplication = { ...(await load()).application!, status: 'approved', reviewSteps: [] }
    expect(humanReviewState(legacy)).toEqual({ kind: 'not_recorded' })
  })

  it('reports a completed review and whether a decision exists', async () => {
    const application = (await load()).application!
    const reviewSteps = application.reviewSteps.map((s) =>
      s.step === 'human_review' ? { ...s, status: 'completed' as const, completedAt: '2026-10-09T10:00:00+01:00' } : s,
    )
    expect(humanReviewState({ ...application, reviewSteps })).toEqual({
      kind: 'completed',
      completedAt: '2026-10-09T10:00:00+01:00',
      decided: false,
    })
    expect(humanReviewState({ ...application, reviewSteps, decisionId: 'dec-x' })).toMatchObject({ decided: true })
  })

  it('lists the missing insurance certificate, then the supplement once provided after submission', async () => {
    const snapshot = await load()
    expect(outstandingDocuments(snapshot.application!).map((d) => d.type)).toEqual(['insurance_certificate'])
    expect(supplementsSinceSubmission(snapshot.application!)).toEqual([])

    const file = { name: 'assurance.pdf', size: 1000, type: 'application/pdf' }
    const next = applyUpload(snapshot, 'insurance_certificate', await uploadDocument(file, { stepMs: 0, now }))
    expect(outstandingDocuments(next.application!)).toEqual([])
    expect(supplementsSinceSubmission(next.application!).map((d) => d.upload?.fileName)).toEqual(['assurance.pdf'])
  })

  it("shows only this application's notifications", async () => {
    const snapshot = await load()
    expect(applicationNotifications(snapshot).map((n) => n.id)).toEqual(['notif-008'])
  })

  it('refreshes without inventing a decision, and fails explicitly in the failure scenario', async () => {
    const snapshot = await load()
    const refreshed = await refreshReviewState(snapshot, { delayMs: 0, now })
    expect(refreshed).toEqual({ state: humanReviewState(snapshot.application), checkedAt: now.toISOString() })
    await expect(refreshReviewState(snapshot, { delayMs: 0, simulateFailure: true })).rejects.toThrow('actualisé')
    expect(scenarioFromSearch('?demo=echec-actualisation')).toBe('refresh-failure')
  })
})
