import { describe, expect, it } from 'vitest'
import { DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, loadOnboardingSnapshot, scenarioFromSearch } from '../src/services/onboardingService'
import { applyRegistration, demoRegistrationInput, submitRegistration } from '../src/services/registrationService'
import {
  applyTechnical,
  canEditTechnical,
  demoTechnicalInput,
  EMPTY_TECHNICAL,
  saveTechnical,
  technicalInputFrom,
  toQuestionnaire,
  validateTechnical,
} from '../src/services/technicalService'
import type { OnboardingSnapshot } from '../src/types/onboarding'

const now = new Date('2026-10-10T13:00:00+01:00')
const load = (scenario: 'nominal' | 'empty' = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

async function registeredDraft() {
  const result = await submitRegistration(demoRegistrationInput(), { delayMs: 0, now })
  if (result.kind !== 'accepted') throw new Error('expected acceptance')
  return applyRegistration(await load('empty'), demoRegistrationInput(), result.receipt)
}

const status = (snapshot: OnboardingSnapshot, id: string) => snapshot.steps.find((s) => s.id === id)!

describe('Technical onboarding questionnaire (MOCKED)', () => {
  it('shows the canonical Cap Azur deployment environment, locked under review', async () => {
    const snapshot = await load()
    const q = snapshot.application!.technicalQuestionnaire!
    expect(q).toMatchObject({
      hostingType: 'virtual_machine',
      operatingSystem: 'Ubuntu Server 22.04',
      cpuCores: 8,
      memoryGb: 32,
      outboundHttpsAllowed: true,
      technicalContactId: 'usr-mehdi',
    })
    expect(canEditTechnical(snapshot.application)).toBe(false)
    expect(status(snapshot, 'technical').status).toBe('completed')
    expect(() => applyTechnical(snapshot, q)).toThrow('brouillon')
  })

  it('requires every answer, an explicit yes or no, and bounded whole numbers', () => {
    expect(Object.keys(validateTechnical(EMPTY_TECHNICAL)).sort()).toEqual(
      [
        'backupsInPlace',
        'bandwidthMbps',
        'containerRuntimeAvailable',
        'cpuCores',
        'dmzAvailable',
        'hostingType',
        'memoryGb',
        'network',
        'operatingSystem',
        'outboundHttpsAllowed',
        'storageGb',
      ].sort(),
    )
    const demo = demoTechnicalInput()
    expect(validateTechnical(demo)).toEqual({})
    expect(Object.keys(validateTechnical({ ...demo, cpuCores: '0', memoryGb: '2.5', storageGb: '100001' })).sort()).toEqual(
      ['cpuCores', 'memoryGb', 'storageGb'],
    )
  })

  it('applies no hardware threshold: small but valid resources are accepted', () => {
    expect(validateTechnical({ ...demoTechnicalInput(), cpuCores: '1', memoryGb: '1', storageGb: '1', containerRuntimeAvailable: 'no' })).toEqual({})
  })

  it('saves a draft questionnaire, completing the technical step but not the DMI step', async () => {
    const draft = await registeredDraft()
    expect(technicalInputFrom(draft.application)).toEqual(EMPTY_TECHNICAL)
    expect(status(draft, 'technical').status).toBe('pending')

    const result = await saveTechnical(demoTechnicalInput(), DEMO_MANAGER_ID, null, { delayMs: 0 })
    if (result.kind !== 'saved') throw new Error('expected save')
    expect(result.questionnaire.dmiSystem).toBeUndefined()
    expect(result.questionnaire.containerRuntimeAvailable).toBe(true)

    const next = applyTechnical(draft, result.questionnaire)
    expect(status(next, 'technical').status).toBe('completed')
    expect(status(next, 'dmi').status).toBe('pending')
    expect(status(next, 'decision').status).toBe('pending')
    expect(next.application!.status).toBe('draft')
  })

  it('keeps DMI / HIS answers already given when the deployment answers change', () => {
    const previous = { ...toQuestionnaire(demoTechnicalInput(), DEMO_MANAGER_ID, null), dmiSystem: 'MediDossier v7', database: 'PostgreSQL 13' }
    const updated = toQuestionnaire({ ...demoTechnicalInput(), memoryGb: '64' }, DEMO_MANAGER_ID, previous)
    expect(updated).toMatchObject({ memoryGb: 64, dmiSystem: 'MediDossier v7', database: 'PostgreSQL 13' })
  })

  it('rejects invalid answers on save and fails explicitly in the failure scenario', async () => {
    expect((await saveTechnical(EMPTY_TECHNICAL, DEMO_MANAGER_ID, null, { delayMs: 0 })).kind).toBe('rejected')
    await expect(
      saveTechnical(demoTechnicalInput(), DEMO_MANAGER_ID, null, { delayMs: 0, simulateFailure: true }),
    ).rejects.toThrow("n'a pas enregistré")
    expect(scenarioFromSearch('?demo=echec-technique')).toBe('technical-failure')
  })
})
