import { describe, expect, it } from 'vitest'
import { DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, loadOnboardingSnapshot, scenarioFromSearch } from '../src/services/onboardingService'
import {
  applyDmi,
  canEditDmi,
  demoDmiInput,
  dmiInputFrom,
  EMPTY_DMI,
  hasTechnicalQuestionnaire,
  NOTES_MAX_LENGTH,
  saveDmi,
  toggleMethod,
  validateDmi,
  withDmiAnswers,
} from '../src/services/dmiService'
import { applyRegistration, demoRegistrationInput, submitRegistration } from '../src/services/registrationService'
import { applyTechnical, demoTechnicalInput, saveTechnical, toQuestionnaire } from '../src/services/technicalService'
import type { OnboardingSnapshot } from '../src/types/onboarding'

const now = new Date('2026-10-10T14:00:00+01:00')
const load = (scenario: 'nominal' | 'empty' = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

async function registeredDraft() {
  const result = await submitRegistration(demoRegistrationInput(), { delayMs: 0, now })
  if (result.kind !== 'accepted') throw new Error('expected acceptance')
  return applyRegistration(await load('empty'), demoRegistrationInput(), result.receipt)
}

async function draftWithTechnical() {
  const draft = await registeredDraft()
  const saved = await saveTechnical(demoTechnicalInput(), DEMO_MANAGER_ID, null, { delayMs: 0 })
  if (saved.kind !== 'saved') throw new Error('expected save')
  return applyTechnical(draft, saved.questionnaire)
}

const dmiStep = (snapshot: OnboardingSnapshot) => snapshot.steps.find((s) => s.id === 'dmi')!

describe('DMI / HIS information questionnaire (MOCKED)', () => {
  it('shows the canonical Cap Azur DMI, locked under review', async () => {
    const snapshot = await load()
    expect(dmiInputFrom(snapshot.application!.technicalQuestionnaire)).toEqual({
      dmiSystem: 'MediDossier v7 (logiciel fictif)',
      database: 'PostgreSQL 13',
      dmiHosting: 'on_premise',
      integrationMethods: ['hl7v2', 'file_export'],
      testEnvironmentAvailable: 'no',
      dmiNotes: "Exports nocturnes uniquement ; pas d'API en temps réel.",
    })
    expect(canEditDmi(snapshot.application)).toBe(false)
    expect(dmiStep(snapshot)).toMatchObject({ status: 'completed', detail: 'DMI déclaré : MediDossier v7 (logiciel fictif).' })
  })

  it('requires the technical questionnaire first', async () => {
    const draft = await registeredDraft()
    expect(hasTechnicalQuestionnaire(draft.application)).toBe(false)
    expect(canEditDmi(draft.application)).toBe(false)
    expect(canEditDmi((await draftWithTechnical()).application)).toBe(true)
  })

  it('validates required answers, integration methods, and note length', () => {
    expect(Object.keys(validateDmi(EMPTY_DMI)).sort()).toEqual(
      ['database', 'dmiHosting', 'dmiSystem', 'integrationMethods', 'testEnvironmentAvailable'].sort(),
    )
    const demo = demoDmiInput()
    expect(validateDmi(demo)).toEqual({})
    expect(validateDmi({ ...demo, dmiNotes: '' })).toEqual({})
    expect(validateDmi({ ...demo, integrationMethods: ['none', 'hl7v2'] })).toHaveProperty('integrationMethods')
    expect(validateDmi({ ...demo, dmiNotes: 'x'.repeat(NOTES_MAX_LENGTH + 1) })).toHaveProperty('dmiNotes')
  })

  it('makes "none" exclusive of the other integration methods', () => {
    expect(toggleMethod(['hl7v2', 'file_export'], 'none', true)).toEqual(['none'])
    expect(toggleMethod(['none'], 'fhir_api', true)).toEqual(['fhir_api'])
    expect(toggleMethod(['hl7v2', 'fhir_api'], 'hl7v2', false)).toEqual(['fhir_api'])
    expect(toggleMethod(['hl7v2'], 'hl7v2', true)).toEqual(['hl7v2'])
  })

  it('saves DMI answers into the draft questionnaire, keeping deployment answers', async () => {
    const draft = await draftWithTechnical()
    expect(dmiStep(draft).status).toBe('pending')

    const result = await saveDmi(draft.application!.technicalQuestionnaire!, { ...demoDmiInput(), dmiNotes: '  ' }, { delayMs: 0 })
    if (result.kind !== 'saved') throw new Error('expected save')
    expect(result.questionnaire).toMatchObject({ cpuCores: 8, memoryGb: 32, dmiSystem: 'MediDossier v7 (logiciel fictif)' })
    expect(result.questionnaire).not.toHaveProperty('dmiNotes')

    const next = applyDmi(draft, result.questionnaire)
    expect(dmiStep(next).status).toBe('completed')
    expect(next.application!.status).toBe('draft')
    expect(next.steps.find((s) => s.id === 'decision')?.status).toBe('pending')
  })

  it('keeps every DMI answer when the technical page saves again', async () => {
    const draft = await draftWithTechnical()
    const withDmi = withDmiAnswers(draft.application!.technicalQuestionnaire!, demoDmiInput())
    const updated = toQuestionnaire({ ...demoTechnicalInput(), memoryGb: '64' }, DEMO_MANAGER_ID, withDmi)
    expect(updated).toEqual({ ...withDmi, memoryGb: 64 })
  })

  it('rejects invalid answers on save, refuses submitted applications, and fails in the failure scenario', async () => {
    const draft = await draftWithTechnical()
    const q = draft.application!.technicalQuestionnaire!
    expect((await saveDmi(q, EMPTY_DMI, { delayMs: 0 })).kind).toBe('rejected')
    await expect(saveDmi(q, demoDmiInput(), { delayMs: 0, simulateFailure: true })).rejects.toThrow("n'a pas enregistré")
    const submitted = await load()
    expect(() => applyDmi(submitted, q)).toThrow('brouillon')
    expect(scenarioFromSearch('?demo=echec-dmi')).toBe('dmi-failure')
  })

  it('collects only descriptive answers, never connection details', () => {
    // Exact allow-list: a new field (address, account, password…) must be added here deliberately.
    expect(Object.keys(EMPTY_DMI).sort()).toEqual(
      ['database', 'dmiHosting', 'dmiNotes', 'dmiSystem', 'integrationMethods', 'testEnvironmentAvailable'].sort(),
    )
    expect(toQuestionnaire(demoTechnicalInput(), DEMO_MANAGER_ID, null)).not.toHaveProperty('dmiSystem')
  })
})
