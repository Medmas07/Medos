import { describe, expect, it } from 'vitest'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  loadOnboardingSnapshot,
  scenarioFromSearch,
} from '../src/services/onboardingService'
import {
  applyProfile,
  canEditProfile,
  demoProfile,
  inputFromProfile,
  profileInputFrom,
  saveProfile,
  toProfile,
  validateProfile,
} from '../src/services/profileService'
import { applyRegistration, demoRegistrationInput, submitRegistration } from '../src/services/registrationService'

const now = new Date('2026-10-10T10:00:00+01:00')
const load = (scenario: 'nominal' | 'empty' = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

async function registeredDraft() {
  const empty = await load('empty')
  const result = await submitRegistration(demoRegistrationInput(), { delayMs: 0, now })
  if (result.kind !== 'accepted') throw new Error('expected acceptance')
  return applyRegistration(empty, demoRegistrationInput(), result.receipt)
}

const stepStatus = (steps: { id: string; status: string; detail: string }[], id: string) =>
  steps.find((s) => s.id === id)

describe('Hospital organization profile (MOCKED)', () => {
  it('reads the canonical Cap Azur profile, without a security contact, and locks it under review', async () => {
    const snapshot = await load()
    const profile = snapshot.application?.administrativeProfile
    expect(profile?.legalName).toBe('Centre Hospitalier Cap Azur')
    expect(profile?.address.city).toBe('Bizerte')
    expect(profile?.securityContact).toBeNull()
    expect(canEditProfile(snapshot.application)).toBe(false)
    expect(stepStatus(snapshot.steps, 'profile')?.detail).toContain('sans contact sécurité')
    expect(() => applyProfile(snapshot, demoProfile())).toThrow('brouillon')
  })

  it('prefills a draft profile from the registration', async () => {
    const draft = await registeredDraft()
    expect(canEditProfile(draft.application)).toBe(true)
    const input = profileInputFrom(draft)
    expect(input.legalName).toBe('Centre Hospitalier Cap Azur')
    expect(input.city).toBe('Bizerte')
    expect(input.registrationNumber).toBe('')
    expect(stepStatus(draft.steps, 'profile')?.status).toBe('pending')
  })

  it('requires the administrative fields and validates formats', async () => {
    const errors = validateProfile(profileInputFrom(await registeredDraft()))
    expect(Object.keys(errors).sort()).toEqual(
      [
        'bedCapacity',
        'dpoEmail',
        'dpoName',
        'email',
        'governorate',
        'legalStatus',
        'phone',
        'postalCode',
        'registrationNumber',
        'representativeName',
        'representativeRole',
        'street',
      ].sort(),
    )
    const demo = inputFromProfile(demoProfile())
    expect(validateProfile(demo)).toEqual({})
    expect(validateProfile({ ...demo, postalCode: '70', bedCapacity: 'beaucoup' })).toMatchObject({
      postalCode: expect.any(String),
      bedCapacity: expect.any(String),
    })
  })

  it('accepts no security contact but rejects a half-filled one', () => {
    const demo = inputFromProfile(demoProfile())
    expect(validateProfile({ ...demo, securityName: '', securityEmail: '' })).toEqual({})
    expect(Object.keys(validateProfile({ ...demo, securityName: 'Rim Jaziri', securityEmail: '' }))).toEqual([
      'securityEmail',
    ])
    expect(Object.keys(validateProfile({ ...demo, securityName: '', securityEmail: 'rssi@cap-azur.example' }))).toEqual(
      ['securityName'],
    )
  })

  it('saves a draft profile and completes the profile step, without approving anything', async () => {
    const draft = await registeredDraft()
    const input = { ...inputFromProfile(demoProfile()), securityName: 'Rim Jaziri', securityEmail: 'rssi@cap-azur.example' }
    const result = await saveProfile(input, { delayMs: 0, now })
    if (result.kind !== 'saved') throw new Error('expected save')
    expect(result.profile).toEqual(toProfile(input, now.toISOString()))

    const next = applyProfile(draft, result.profile)
    expect(next.application?.administrativeProfile?.securityContact?.fullName).toBe('Rim Jaziri')
    expect(next.application?.status).toBe('draft')
    expect(stepStatus(next.steps, 'profile')).toMatchObject({ status: 'completed', detail: 'Profil renseigné.' })
    expect(stepStatus(next.steps, 'decision')?.status).toBe('pending')
    expect(stepStatus(next.steps, 'node-download')?.status).toBe('locked')
  })

  it('rejects invalid input on save and fails explicitly in the failure scenario', async () => {
    const draft = await registeredDraft()
    const rejected = await saveProfile(profileInputFrom(draft), { delayMs: 0 })
    expect(rejected.kind).toBe('rejected')
    await expect(saveProfile(inputFromProfile(demoProfile()), { delayMs: 0, simulateFailure: true })).rejects.toThrow(
      "n'a pas enregistré",
    )
    expect(scenarioFromSearch('?demo=echec-profil')).toBe('profile-failure')
  })
})
