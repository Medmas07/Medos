import governanceFixtures from '../../../../../demo-data/governance.json'
import type {
  DmiHosting,
  HospitalApplication,
  IntegrationMethod,
  OnboardingSnapshot,
  TechnicalQuestionnaire,
} from '../types/onboarding'
import { deriveSteps, DEMO_ORGANIZATION_ID } from './onboardingService'

/**
 * MOCKED DMI / HIS information questionnaire (HC-056). The answers only prepare
 * the DMI Adapter that will run locally inside the Hospital Node; nothing here
 * connects to a DMI, and no central service ever does. Credentials, internal
 * addresses, and patient data must never be entered. Saving is simulated and
 * kept in memory only.
 */

type YesNo = 'yes' | 'no' | ''

export interface DmiInput {
  dmiSystem: string
  database: string
  dmiHosting: DmiHosting | ''
  integrationMethods: IntegrationMethod[]
  testEnvironmentAvailable: YesNo
  dmiNotes: string
}

export type DmiField = keyof DmiInput
export type DmiErrors = Partial<Record<DmiField, string>>

export const DMI_HOSTING_LABELS: Record<DmiHosting, string> = {
  on_premise: "Hébergé dans l'établissement",
  vendor_hosted: "Hébergé par l'éditeur",
}

export const INTEGRATION_LABELS: Record<IntegrationMethod, { label: string; hint: string }> = {
  hl7v2: { label: 'Messages HL7 v2', hint: 'Flux de messages émis par le DMI.' },
  fhir_api: { label: 'API FHIR', hint: 'API exposée par le DMI ou son éditeur.' },
  file_export: { label: 'Export de fichiers', hint: 'Exports périodiques (CSV, XML…).' },
  database_replica: { label: 'Réplique de base en lecture seule', hint: 'Copie dédiée, jamais la base de production.' },
  none: { label: 'Aucune méthode connue', hint: "À étudier avec l'éditeur." },
}

export const NOTES_MAX_LENGTH = 500

/** The DMI page needs the technical questionnaire (HC-055) it completes. */
export function hasTechnicalQuestionnaire(application: HospitalApplication | null): boolean {
  return Boolean(application?.technicalQuestionnaire)
}

/** The DMI answers can be edited only before the application is submitted. */
export function canEditDmi(application: HospitalApplication | null): boolean {
  return application?.status === 'draft' && hasTechnicalQuestionnaire(application)
}

/** Whether the questionnaire already holds DMI / HIS answers. */
export function hasDmiAnswers(questionnaire: TechnicalQuestionnaire | null | undefined): boolean {
  return Boolean(questionnaire?.dmiSystem && questionnaire.integrationMethods?.length)
}

export const EMPTY_DMI: DmiInput = {
  dmiSystem: '',
  database: '',
  dmiHosting: '',
  integrationMethods: [],
  testEnvironmentAvailable: '',
  dmiNotes: '',
}

export function dmiInputFrom(questionnaire: TechnicalQuestionnaire | null | undefined): DmiInput {
  if (!questionnaire || !hasDmiAnswers(questionnaire)) return EMPTY_DMI
  return {
    dmiSystem: questionnaire.dmiSystem ?? '',
    database: questionnaire.database ?? '',
    dmiHosting: questionnaire.dmiHosting ?? '',
    integrationMethods: questionnaire.integrationMethods ?? [],
    testEnvironmentAvailable:
      questionnaire.testEnvironmentAvailable === undefined ? '' : questionnaire.testEnvironmentAvailable ? 'yes' : 'no',
    dmiNotes: questionnaire.dmiNotes ?? '',
  }
}

/** The canonical fictional Cap Azur answers (HC-005 fixtures), for demonstrations. */
export function demoDmiInput(): DmiInput {
  const applications = governanceFixtures.hospitalApplications as unknown as HospitalApplication[]
  return dmiInputFrom(applications.find((a) => a.organizationId === DEMO_ORGANIZATION_ID)!.technicalQuestionnaire)
}

/** "None" excludes every other method; choosing a real method removes "none". Pure. */
export function toggleMethod(methods: IntegrationMethod[], method: IntegrationMethod, checked: boolean): IntegrationMethod[] {
  if (!checked) return methods.filter((m) => m !== method)
  if (method === 'none') return ['none']
  return [...methods.filter((m) => m !== 'none' && m !== method), method]
}

/** Validates every answer. Pure. */
export function validateDmi(input: DmiInput): DmiErrors {
  const errors: DmiErrors = {}
  if (input.dmiSystem.trim() === '') errors.dmiSystem = 'Indiquez le DMI / SIH utilisé (produit et version).'
  if (input.database.trim() === '') errors.database = 'Indiquez la base de données du DMI (moteur et version).'
  if (input.dmiHosting === '') errors.dmiHosting = "Indiquez où le DMI est hébergé."
  if (input.integrationMethods.length === 0) {
    errors.integrationMethods = "Cochez au moins une méthode, ou « Aucune méthode connue »."
  } else if (input.integrationMethods.includes('none') && input.integrationMethods.length > 1) {
    errors.integrationMethods = "« Aucune méthode connue » ne peut pas être combinée à une autre méthode."
  }
  if (input.testEnvironmentAvailable === '') errors.testEnvironmentAvailable = 'Répondez par oui ou non.'
  if (input.dmiNotes.length > NOTES_MAX_LENGTH) errors.dmiNotes = `${NOTES_MAX_LENGTH} caractères au maximum.`
  return errors
}

/** Merges valid DMI answers into the technical questionnaire. Call only without validation errors. Pure. */
export function withDmiAnswers(questionnaire: TechnicalQuestionnaire, input: DmiInput): TechnicalQuestionnaire {
  const notes = input.dmiNotes.trim()
  const { dmiNotes: _previousNotes, ...rest } = questionnaire
  return {
    ...rest,
    dmiSystem: input.dmiSystem.trim(),
    database: input.database.trim(),
    dmiHosting: input.dmiHosting as DmiHosting,
    integrationMethods: [...input.integrationMethods],
    testEnvironmentAvailable: input.testEnvironmentAvailable === 'yes',
    ...(notes && { dmiNotes: notes }),
  }
}

export type DmiSaveResult =
  | { kind: 'saved'; questionnaire: TechnicalQuestionnaire }
  | { kind: 'rejected'; errors: DmiErrors }

export interface SaveOptions {
  simulateFailure?: boolean
  delayMs?: number
}

/** Simulated save: re-validates, as a server would. */
export async function saveDmi(
  questionnaire: TechnicalQuestionnaire,
  input: DmiInput,
  { simulateFailure = false, delayMs = 600 }: SaveOptions = {},
): Promise<DmiSaveResult> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("Le service d'adhésion simulé n'a pas enregistré les informations DMI (scénario de démonstration).")
  }
  const errors = validateDmi(input)
  if (Object.keys(errors).length > 0) return { kind: 'rejected', errors }
  return { kind: 'saved', questionnaire: withDmiAnswers(questionnaire, input) }
}

/** Returns the snapshot with the updated questionnaire on the draft application. Pure. */
export function applyDmi(snapshot: OnboardingSnapshot, questionnaire: TechnicalQuestionnaire): OnboardingSnapshot {
  if (!canEditDmi(snapshot.application)) {
    throw new Error('Les informations DMI ne peuvent être modifiées que sur une inscription en brouillon.')
  }
  const application = { ...snapshot.application!, technicalQuestionnaire: questionnaire }
  return { ...snapshot, application, steps: deriveSteps(snapshot.organization, application) }
}
