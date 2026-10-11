import type {
  AgreementCode,
  ApplicationAgreement,
  HospitalApplication,
  OnboardingSnapshot,
} from '../types/onboarding'
import { deriveSteps } from './onboardingService'

/**
 * MOCKED agreements workflow (HC-054). The agreement texts below are fictional
 * demonstration summaries with no legal value. Acceptance is recorded by a
 * simulated service and kept in memory only. An agreement contract is PLANNED.
 */

export interface AgreementTemplate {
  code: AgreementCode
  title: string
  version: string
  summary: string
  /** Key clauses, restating the ecosystem's product invariants. */
  clauses: readonly string[]
}

export const AGREEMENT_TEMPLATES: readonly AgreementTemplate[] = [
  {
    code: 'data_processing_agreement',
    title: 'Accord de traitement des données',
    version: '1.0',
    summary: "Encadre le traitement des données cliniques au sein de l'écosystème fédéré.",
    clauses: [
      "Les données cliniques restent sous le contrôle de l'établissement, dans son Hospital Node.",
      "Aucun service central n'accède directement au DMI de l'établissement.",
      'Tout partage entre établissements exige une autorisation explicite : périmètre, finalité, durée et consentement.',
      'La recherche se fait par compute-to-data : aucun export brut des données vers les chercheurs.',
      "Chaque accès est journalisé ; aucune donnée médicale n'est inscrite dans un registre de preuves.",
    ],
  },
  {
    code: 'governance_charter',
    title: 'Charte de gouvernance fédérée',
    version: '1.0',
    summary: "Fixe le rôle de l'Autorité de gouvernance et d'éthique et les engagements des membres.",
    clauses: [
      "L'Autorité de gouvernance et d'éthique décide des adhésions, des synchronisations et des accès recherche.",
      "L'opérateur de la plateforme ne peut pas approuver ses propres demandes.",
      "Les sorties d'IA sont indicatives et restent soumises à une validation humaine.",
      "L'établissement signale à l'Autorité tout incident de sécurité affectant son Hospital Node.",
    ],
  },
]

/** One entry per required agreement, from the application or not yet accepted. Pure. */
export function agreementChecklist(application: HospitalApplication): ApplicationAgreement[] {
  return AGREEMENT_TEMPLATES.map(
    (template) =>
      application.agreements.find((a) => a.code === template.code) ?? {
        code: template.code,
        title: template.title,
        accepted: false,
      },
  )
}

/** Agreements can be accepted or withdrawn only before the application is submitted. */
export function canChangeAgreements(application: HospitalApplication | null): boolean {
  return application?.status === 'draft'
}

export interface AcceptOptions {
  /** Simulates an unavailable service (demo scenario). */
  simulateFailure?: boolean
  delayMs?: number
  now?: Date
}

/**
 * Simulated acceptance. Requires the explicit "read and accept" confirmation and
 * records the accepted version, the date, and the signatory.
 */
export async function acceptAgreement(
  code: AgreementCode,
  confirmed: boolean,
  signatoryId: string,
  { simulateFailure = false, delayMs = 500, now = new Date() }: AcceptOptions = {},
): Promise<ApplicationAgreement> {
  if (!confirmed) throw new Error("Confirmez avoir lu l'accord avant de l'accepter.")
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("Le service d'adhésion simulé n'a pas enregistré l'acceptation (scénario de démonstration).")
  }
  const template = AGREEMENT_TEMPLATES.find((t) => t.code === code)!
  return {
    code,
    title: template.title,
    accepted: true,
    version: template.version,
    acceptedAt: now.toISOString(),
    acceptedById: signatoryId,
  }
}

function withAgreements(snapshot: OnboardingSnapshot, agreements: ApplicationAgreement[]): OnboardingSnapshot {
  const application = { ...snapshot.application!, agreements }
  return { ...snapshot, application, steps: deriveSteps(snapshot.organization, application) }
}

/** Returns the snapshot with this acceptance recorded (draft only). Pure. */
export function applyAcceptance(snapshot: OnboardingSnapshot, accepted: ApplicationAgreement): OnboardingSnapshot {
  if (!canChangeAgreements(snapshot.application)) throw new Error('Les accords ne peuvent plus être modifiés.')
  return withAgreements(
    snapshot,
    agreementChecklist(snapshot.application!).map((a) => (a.code === accepted.code ? accepted : a)),
  )
}

/** Returns the snapshot with this acceptance withdrawn (draft only). Pure. */
export function applyWithdrawal(snapshot: OnboardingSnapshot, code: AgreementCode): OnboardingSnapshot {
  if (!canChangeAgreements(snapshot.application)) throw new Error('Les accords ne peuvent plus être modifiés.')
  return withAgreements(
    snapshot,
    agreementChecklist(snapshot.application!).map((a) =>
      a.code === code ? { code, title: a.title, accepted: false } : a,
    ),
  )
}
