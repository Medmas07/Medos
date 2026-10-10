import { describe, expect, it } from 'vitest'
import { acceptAgreement, applyAcceptance } from '../src/services/agreementService'
import { applyDmi, demoDmiInput, withDmiAnswers } from '../src/services/dmiService'
import { applyUpload, REQUIRED_DOCUMENTS, uploadDocument } from '../src/services/documentService'
import { DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, loadOnboardingSnapshot, scenarioFromSearch } from '../src/services/onboardingService'
import { applyProfile, demoProfile } from '../src/services/profileService'
import { applyRegistration, demoRegistrationInput, submitRegistration } from '../src/services/registrationService'
import {
  ASSISTED_REVIEW_PROVENANCE,
  assistedFindings,
  canSubmit,
  completenessFindings,
  runAutomatedReview,
  submitForReview,
} from '../src/services/reviewService'
import { applyTechnical, demoTechnicalInput, toQuestionnaire } from '../src/services/technicalService'
import type { OnboardingSnapshot } from '../src/types/onboarding'

const now = new Date('2026-10-10T15:00:00+01:00')
const load = (scenario: 'nominal' | 'empty' = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

async function registeredDraft() {
  const result = await submitRegistration(demoRegistrationInput(), { delayMs: 0, now })
  if (result.kind !== 'accepted') throw new Error('expected acceptance')
  return applyRegistration(await load('empty'), demoRegistrationInput(), result.receipt)
}

/** A draft with every step completed from the canonical fictional example. */
async function completeDraft(): Promise<OnboardingSnapshot> {
  let snapshot = await registeredDraft()
  snapshot = applyProfile(snapshot, demoProfile())
  for (const { type } of REQUIRED_DOCUMENTS) {
    snapshot = applyUpload(snapshot, type, await uploadDocument({ name: `${type}.pdf`, size: 1000, type: 'application/pdf' }, { stepMs: 0, now }))
  }
  for (const code of ['data_processing_agreement', 'governance_charter'] as const) {
    snapshot = applyAcceptance(snapshot, await acceptAgreement(code, true, DEMO_MANAGER_ID, { delayMs: 0, now }))
  }
  snapshot = applyTechnical(snapshot, toQuestionnaire(demoTechnicalInput(), DEMO_MANAGER_ID, null))
  return applyDmi(snapshot, withDmiAnswers(snapshot.application!.technicalQuestionnaire!, demoDmiInput()))
}

const step = (snapshot: OnboardingSnapshot, id: string) => snapshot.steps.find((s) => s.id === id)!

describe('Automated onboarding review (MOCKED)', () => {
  it('lists every missing step of a fresh draft, each linked to its page', async () => {
    const findings = completenessFindings(await registeredDraft())
    expect(findings.map((f) => f.step)).toEqual([
      'profile',
      'documents',
      'documents',
      'documents',
      'agreements',
      'agreements',
      'technical',
    ])
    expect(findings.map((f) => f.message)).toContain("Attestation d'assurance manquante.")
    expect(findings.map((f) => f.message)).toContain('Charte de gouvernance fédérée non acceptée.')
  })

  it('asks for the DMI questionnaire once the technical one exists', async () => {
    const draft = await registeredDraft()
    const withTechnical = applyTechnical(draft, toQuestionnaire(demoTechnicalInput(), DEMO_MANAGER_ID, null))
    expect(completenessFindings(withTechnical).at(-1)).toEqual({ message: 'Questionnaire DMI / SIH non complété.', step: 'dmi' })
  })

  it('finds a complete draft complete, with advisory remarks matching the fixture story', async () => {
    const draft = await completeDraft()
    expect(completenessFindings(draft)).toEqual([])
    expect(assistedFindings(draft).map((f) => f.message)).toEqual([
      "Aucun contact de sécurité distinct n'est indiqué.",
      "Pas d'environnement de test du DMI : l'adaptateur devra être vérifié sur des données fictives.",
    ])
  })

  it('flags inconsistencies between the registration and the profile', async () => {
    const draft = await completeDraft()
    const profile = { ...demoProfile(), legalName: 'Clinique Autre Nom', address: { ...demoProfile().address, city: 'Tunis' } }
    const messages = assistedFindings(applyProfile(draft, profile)).map((f) => f.message)
    expect(messages).toContain("La raison sociale du profil diffère du nom déclaré à l'inscription.")
    expect(messages).toContain("La ville du profil diffère de celle déclarée à l'inscription.")
  })

  it('never lets assisted remarks block submission, only completeness findings', async () => {
    const draft = await completeDraft()
    const result = await runAutomatedReview(draft, { delayMs: 0, now })
    expect(result.assisted.length).toBeGreaterThan(0)
    expect(canSubmit(draft.application, result)).toBe(true)

    const incomplete = await runAutomatedReview(await registeredDraft(), { delayMs: 0, now })
    expect(canSubmit((await registeredDraft()).application, incomplete)).toBe(false)
  })

  it('submits for human review without approving, recording mocked and advisory results', async () => {
    const draft = await completeDraft()
    const submitted = await submitForReview(draft, true, { delayMs: 0, now })
    const application = submitted.application!
    expect(application.status).toBe('human_review')
    expect(application.decisionId).toBeNull()
    expect(application.submittedAt).toBe(now.toISOString())
    expect(application.reviewSteps).toEqual([
      { step: 'completeness_check', status: 'completed', completedAt: now.toISOString(), findings: [] },
      {
        step: 'assisted_review',
        status: 'completed_with_findings',
        completedAt: now.toISOString(),
        mocked: true,
        advisory: true,
        findings: assistedFindings(draft).map((f) => f.message),
      },
      { step: 'human_review', status: 'pending', completedAt: null, findings: [] },
    ])
    expect(step(submitted, 'automated-review')).toMatchObject({ status: 'completed', detail: 'Dossier complet ; 2 remarques indicative(s).' })
    expect(step(submitted, 'human-review').status).toBe('in_progress')
    expect(step(submitted, 'decision').status).toBe('pending')
    expect(step(submitted, 'node-download').status).toBe('locked')
  })

  it('refuses unconfirmed, incomplete, already-submitted, and failed submissions', async () => {
    const draft = await completeDraft()
    await expect(submitForReview(draft, false, { delayMs: 0 })).rejects.toThrow('Confirmez')
    await expect(submitForReview(await registeredDraft(), true, { delayMs: 0 })).rejects.toThrow('incomplet')
    await expect(submitForReview(await load(), true, { delayMs: 0 })).rejects.toThrow('brouillon')
    await expect(submitForReview(draft, true, { delayMs: 0, simulateFailure: true })).rejects.toThrow("n'a pas reçu")
    expect(scenarioFromSearch('?demo=echec-soumission')).toBe('submission-failure')
  })

  it('keeps the fixture application blocked on its completeness finding, not on advisory remarks', async () => {
    const snapshot = await load()
    expect(step(snapshot, 'automated-review')).toMatchObject({ status: 'attention', detail: 'Complétude : 1 point à corriger.' })
    expect(ASSISTED_REVIEW_PROVENANCE).toContain("aucun modèle d'IA n'est appelé")
  })
})
