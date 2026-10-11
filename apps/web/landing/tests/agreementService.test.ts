import { describe, expect, it } from 'vitest'
import { DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, loadOnboardingSnapshot, scenarioFromSearch } from '../src/services/onboardingService'
import {
  acceptAgreement,
  AGREEMENT_TEMPLATES,
  agreementChecklist,
  applyAcceptance,
  applyWithdrawal,
  canChangeAgreements,
} from '../src/services/agreementService'
import { applyRegistration, demoRegistrationInput, submitRegistration } from '../src/services/registrationService'
import type { OnboardingSnapshot } from '../src/types/onboarding'

const now = new Date('2026-10-10T12:00:00+01:00')
const accept = (code: 'data_processing_agreement' | 'governance_charter', confirmed = true, simulateFailure = false) =>
  acceptAgreement(code, confirmed, DEMO_MANAGER_ID, { delayMs: 0, now, simulateFailure })

const load = (scenario: 'nominal' | 'empty' = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

async function registeredDraft() {
  const result = await submitRegistration(demoRegistrationInput(), { delayMs: 0, now })
  if (result.kind !== 'accepted') throw new Error('expected acceptance')
  return applyRegistration(await load('empty'), demoRegistrationInput(), result.receipt)
}

const step = (snapshot: OnboardingSnapshot) => snapshot.steps.find((s) => s.id === 'agreements')!

describe('Hospital agreements workflow (MOCKED)', () => {
  it('shows the two canonical acceptances of Cap Azur, locked under review', async () => {
    const snapshot = await load()
    const checklist = agreementChecklist(snapshot.application!)
    expect(checklist.map((a) => [a.code, a.accepted, a.version, a.acceptedById])).toEqual([
      ['data_processing_agreement', true, '1.0', 'usr-mehdi'],
      ['governance_charter', true, '1.0', 'usr-mehdi'],
    ])
    expect(canChangeAgreements(snapshot.application)).toBe(false)
    expect(step(snapshot).status).toBe('completed')
    expect(() => applyWithdrawal(snapshot, 'governance_charter')).toThrow('ne peuvent plus')
  })

  it('restates the ecosystem invariants in the fictional agreement texts', () => {
    const text = AGREEMENT_TEMPLATES.flatMap((t) => t.clauses).join(' ')
    expect(text).toContain('compute-to-data')
    expect(text).toContain("L'Autorité de gouvernance et d'éthique décide")
    expect(text).toContain('validation humaine')
    expect(AGREEMENT_TEMPLATES.map((t) => t.code)).toEqual(['data_processing_agreement', 'governance_charter'])
  })

  it('requires the explicit read-and-accept confirmation', async () => {
    await expect(accept('governance_charter', false)).rejects.toThrow('Confirmez')
  })

  it('records version, date, and signatory, and tracks draft progress until complete', async () => {
    let snapshot = await registeredDraft()
    expect(step(snapshot).status).toBe('pending')
    expect(agreementChecklist(snapshot.application!).every((a) => !a.accepted)).toBe(true)

    const record = await accept('data_processing_agreement')
    expect(record).toEqual({
      code: 'data_processing_agreement',
      title: 'Accord de traitement des données',
      accepted: true,
      version: '1.0',
      acceptedAt: now.toISOString(),
      acceptedById: 'usr-mehdi',
    })
    snapshot = applyAcceptance(snapshot, record)
    expect(step(snapshot)).toMatchObject({ status: 'in_progress', detail: '1 / 2 accords acceptés.' })

    snapshot = applyAcceptance(snapshot, await accept('governance_charter'))
    expect(step(snapshot).status).toBe('completed')
    expect(snapshot.application!.status).toBe('draft')
    expect(snapshot.steps.find((s) => s.id === 'decision')?.status).toBe('pending')

    snapshot = applyWithdrawal(snapshot, 'data_processing_agreement')
    expect(snapshot.application!.agreements.find((a) => a.code === 'data_processing_agreement')).toEqual({
      code: 'data_processing_agreement',
      title: 'Accord de traitement des données',
      accepted: false,
    })
    expect(step(snapshot).detail).toBe('1 / 2 accords acceptés.')
  })

  it('fails explicitly in the failure scenario', async () => {
    await expect(accept('governance_charter', true, true)).rejects.toThrow("n'a pas enregistré")
    expect(scenarioFromSearch('?demo=echec-accord')).toBe('agreement-failure')
  })
})
