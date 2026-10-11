import { describe, expect, it } from 'vitest'
import { DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, loadOnboardingSnapshot, scenarioFromSearch } from '../src/services/onboardingService'
import {
  applyRegistration,
  demoRegistrationInput,
  EMPTY_REGISTRATION,
  firstStepWithError,
  REGISTRATION_STEPS,
  submitRegistration,
  validateRegistration,
} from '../src/services/registrationService'

const now = new Date('2026-10-10T09:30:00+01:00')
const submit = (input = demoRegistrationInput(), simulateFailure = false) =>
  submitRegistration(input, { delayMs: 0, now, simulateFailure })

describe('Hospital registration (MOCKED)', () => {
  it('fills the demo example from the canonical Cap Azur fixtures', () => {
    const input = demoRegistrationInput()
    expect(input.organizationName).toBe('Centre Hospitalier Cap Azur')
    expect(input.managerLastName).toBe('Sassi')
    expect(input.managerEmail.endsWith('.example')).toBe(true)
    expect(validateRegistration(input)).toEqual({})
  })

  it('requires every field and both confirmations, step by step', () => {
    const errors = validateRegistration(EMPTY_REGISTRATION)
    expect(Object.keys(errors).sort()).toEqual(REGISTRATION_STEPS.flatMap((s) => s.fields).sort())
    expect(firstStepWithError(errors)).toBe(0)

    const managerOnly = validateRegistration(
      { ...demoRegistrationInput(), managerEmail: 'pas-un-email', managerPhone: '12' },
      REGISTRATION_STEPS[1].fields,
    )
    expect(Object.keys(managerOnly).sort()).toEqual(['managerEmail', 'managerPhone'])
    expect(firstStepWithError(managerOnly)).toBe(1)

    const unconfirmed = validateRegistration({ ...demoRegistrationInput(), acknowledgesGovernance: false })
    expect(unconfirmed).toEqual({ acknowledgesGovernance: 'Cette confirmation est obligatoire.' })
  })

  it('accepts a valid registration with a deterministic reference', async () => {
    const result = await submit()
    expect(result).toEqual({
      kind: 'accepted',
      receipt: { reference: 'REG-20261010-CHCAPAZUR', submittedAt: now.toISOString() },
    })
  })

  it('rejects an establishment already registered in the fictional registry', async () => {
    const result = await submit({ ...demoRegistrationInput(), organizationName: 'hopital universitaire BAB ENNOUR' })
    expect(result.kind).toBe('rejected')
    if (result.kind === 'rejected') {
      expect(result.errors.organizationName).toContain('déjà enregistré')
      expect(firstStepWithError(result.errors)).toBe(0)
    }
  })

  it('fails explicitly in the simulated failure scenario', async () => {
    await expect(submit(demoRegistrationInput(), true)).rejects.toThrow("n'a pas répondu")
  })

  it('creates a local draft application that is never approved', async () => {
    const empty = await loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, {
      scenario: 'registration-failure',
      delayMs: 0,
    })
    expect(empty.application).toBeNull()

    const result = await submit({ ...demoRegistrationInput(), city: '  Bizerte  ' })
    if (result.kind !== 'accepted') throw new Error('expected acceptance')
    const registered = applyRegistration(empty, { ...demoRegistrationInput(), city: '  Bizerte  ' }, result.receipt)

    expect(registered.application).toMatchObject({ id: 'REG-20261010-CHCAPAZUR', status: 'draft', decisionId: null })
    expect(registered.organization.city).toBe('Bizerte')
    expect(registered.organization.governanceStatus).toBe(empty.organization.governanceStatus)
    expect(registered.manager.email).toBe('mehdi.sassi@cap-azur.example')

    const status = Object.fromEntries(registered.steps.map((s) => [s.id, s.status]))
    expect(status.registration).toBe('completed')
    expect(status.profile).toBe('pending')
    expect(status.decision).toBe('pending')
    expect(status['node-download']).toBe('locked')
  })

  it('maps the registration failure query parameter', () => {
    expect(scenarioFromSearch('?demo=echec-inscription')).toBe('registration-failure')
  })
})
