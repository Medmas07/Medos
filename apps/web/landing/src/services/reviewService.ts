import type { AgreementCode, DocumentType, HospitalApplication, OnboardingSnapshot, ReviewStep, StepId } from '../types/onboarding'
import { agreementChecklist } from './agreementService'
import { hasDmiAnswers } from './dmiService'
import { documentChecklist } from './documentService'
import { deriveSteps } from './onboardingService'

/**
 * MOCKED automated onboarding review (HC-057), as the product vision orders it:
 * a deterministic completeness check, then an optional assisted review that only
 * looks for inconsistencies, then human review by the Governance / Ethics
 * Authority. The assisted review is SIMULATED: fixed rules stand in for an LLM,
 * no model is called, and its remarks are advisory and never block. Nothing here
 * approves an application.
 */

export interface Finding {
  message: string
  /** Portal page where the point can be corrected. */
  step?: StepId
}

export interface ReviewResult {
  completeness: Finding[]
  assisted: Finding[]
  ranAt: string
}

/** Provenance shown with every assisted-review result. */
export const ASSISTED_REVIEW_PROVENANCE =
  "Revue assistée simulée : règles déterministes de démonstration, aucun modèle d'IA n'est appelé. Remarques indicatives, à confirmer par une revue humaine."

const MISSING_DOCUMENT: Record<DocumentType, string> = {
  statutes: "Statuts de l'établissement manquants.",
  operating_license: "Autorisation d'exercice manquante.",
  insurance_certificate: "Attestation d'assurance manquante.",
}

const NOT_ACCEPTED: Record<AgreementCode, string> = {
  data_processing_agreement: 'Accord de traitement des données non accepté.',
  governance_charter: 'Charte de gouvernance fédérée non acceptée.',
}

/** Blocking: every onboarding step that precedes the review must be complete. Pure. */
export function completenessFindings(snapshot: OnboardingSnapshot): Finding[] {
  const application = snapshot.application
  if (!application) return [{ message: "Aucune inscription : inscrivez d'abord l'établissement.", step: 'registration' }]
  const findings: Finding[] = []
  if (!application.administrativeProfile) {
    findings.push({ message: "Profil administratif de l'établissement non renseigné.", step: 'profile' })
  }
  for (const document of documentChecklist(application)) {
    if (document.status !== 'received') findings.push({ message: MISSING_DOCUMENT[document.type], step: 'documents' })
  }
  for (const agreement of agreementChecklist(application)) {
    if (!agreement.accepted) findings.push({ message: NOT_ACCEPTED[agreement.code], step: 'agreements' })
  }
  const questionnaire = application.technicalQuestionnaire
  if (!questionnaire) {
    findings.push({ message: 'Questionnaire technique non complété.', step: 'technical' })
  } else if (!hasDmiAnswers(questionnaire)) {
    findings.push({ message: 'Questionnaire DMI / SIH non complété.', step: 'dmi' })
  }
  return findings
}

const normalize = (text: string) =>
  text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()

/** Advisory only: simulated inconsistency checks across the dossier. Pure. */
export function assistedFindings(snapshot: OnboardingSnapshot): Finding[] {
  const { application, organization } = snapshot
  if (!application) return []
  const findings: Finding[] = []
  const profile = application.administrativeProfile
  if (profile) {
    if (normalize(profile.legalName) !== normalize(organization.name)) {
      findings.push({ message: "La raison sociale du profil diffère du nom déclaré à l'inscription.", step: 'profile' })
    }
    if (normalize(profile.address.city) !== normalize(organization.city)) {
      findings.push({ message: "La ville du profil diffère de celle déclarée à l'inscription.", step: 'profile' })
    }
    if (!profile.securityContact) {
      findings.push({ message: "Aucun contact de sécurité distinct n'est indiqué.", step: 'profile' })
    }
  }
  const q = application.technicalQuestionnaire
  if (q && hasDmiAnswers(q)) {
    if (q.integrationMethods?.includes('none')) {
      findings.push({ message: "Aucune méthode d'intégration du DMI n'est connue : l'adaptateur DMI sera à étudier avec l'éditeur.", step: 'dmi' })
    }
    if (q.testEnvironmentAvailable === false) {
      findings.push({ message: "Pas d'environnement de test du DMI : l'adaptateur devra être vérifié sur des données fictives.", step: 'dmi' })
    }
  }
  if (q && !q.outboundHttpsAllowed) {
    findings.push({ message: 'Les connexions HTTPS sortantes sont refusées : la connectivité du futur Hospital Node est à vérifier.', step: 'technical' })
  }
  return findings
}

export interface RunOptions {
  delayMs?: number
  now?: Date
}

/** Simulated run of both automated checks on the current dossier. */
export async function runAutomatedReview(
  snapshot: OnboardingSnapshot,
  { delayMs = 900, now = new Date() }: RunOptions = {},
): Promise<ReviewResult> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  return { completeness: completenessFindings(snapshot), assisted: assistedFindings(snapshot), ranAt: now.toISOString() }
}

/** A draft can be submitted once the completeness check finds nothing. */
export function canSubmit(application: HospitalApplication | null, result: ReviewResult | null): boolean {
  return application?.status === 'draft' && result !== null && result.completeness.length === 0
}

export interface SubmitOptions {
  /** Simulates an unavailable service (demo scenario). */
  simulateFailure?: boolean
  delayMs?: number
  now?: Date
}

/**
 * Simulated submission for human review. The checks run again on the submitted
 * dossier, as a server would. The application moves to `human_review`, with a
 * pending human-review step; it is not approved.
 */
export async function submitForReview(
  snapshot: OnboardingSnapshot,
  confirmed: boolean,
  { simulateFailure = false, delayMs = 700, now = new Date() }: SubmitOptions = {},
): Promise<OnboardingSnapshot> {
  if (!confirmed) throw new Error('Confirmez la transmission du dossier.')
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("Le service d'adhésion simulé n'a pas reçu le dossier (scénario de démonstration).")
  }
  const application = snapshot.application
  if (application?.status !== 'draft') throw new Error('Seule une inscription en brouillon peut être transmise.')
  const completeness = completenessFindings(snapshot)
  if (completeness.length > 0) throw new Error('Le dossier est incomplet : corrigez les points signalés.')
  const assisted = assistedFindings(snapshot)
  const at = now.toISOString()
  const reviewSteps: ReviewStep[] = [
    { step: 'completeness_check', status: 'completed', completedAt: at, findings: [] },
    {
      step: 'assisted_review',
      status: assisted.length > 0 ? 'completed_with_findings' : 'completed',
      completedAt: at,
      mocked: true,
      advisory: true,
      findings: assisted.map((f) => f.message),
    },
    { step: 'human_review', status: 'pending', completedAt: null, findings: [] },
  ]
  const submitted: HospitalApplication = { ...application, status: 'human_review', submittedAt: at, reviewSteps }
  return { ...snapshot, application: submitted, steps: deriveSteps(snapshot.organization, submitted) }
}
