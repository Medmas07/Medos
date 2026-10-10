import governanceFixtures from '../../../../../demo-data/governance.json'
import type { HospitalApplication, HostingType, OnboardingSnapshot, TechnicalQuestionnaire } from '../types/onboarding'
import { deriveSteps, DEMO_ORGANIZATION_ID } from './onboardingService'

/**
 * MOCKED technical onboarding questionnaire (HC-055): the deployment
 * environment of the future Hospital Node. Answers are only collected and
 * validated; no hardware threshold or readiness verdict is applied, because no
 * requirement defines one. Saving is simulated and kept in memory only.
 */

type YesNo = 'yes' | 'no' | ''

export interface TechnicalInput {
  hostingType: HostingType | ''
  operatingSystem: string
  cpuCores: string
  memoryGb: string
  storageGb: string
  bandwidthMbps: string
  network: string
  dmzAvailable: YesNo
  outboundHttpsAllowed: YesNo
  containerRuntimeAvailable: YesNo
  backupsInPlace: YesNo
}

export type TechnicalField = keyof TechnicalInput
export type TechnicalErrors = Partial<Record<TechnicalField, string>>

export const HOSTING_LABELS: Record<HostingType, string> = {
  on_premise: 'Serveur physique sur site',
  virtual_machine: 'Machine virtuelle sur site',
  private_cloud: 'Cloud privé de l’établissement',
}

export const YES_NO_FIELDS = [
  'dmzAvailable',
  'outboundHttpsAllowed',
  'containerRuntimeAvailable',
  'backupsInPlace',
] as const satisfies readonly TechnicalField[]

export const QUESTION_LABELS: Record<(typeof YES_NO_FIELDS)[number], string> = {
  dmzAvailable: 'Zone démilitarisée (DMZ) disponible',
  outboundHttpsAllowed: 'Connexions HTTPS sortantes autorisées',
  containerRuntimeAvailable: "Exécution de conteneurs possible sur l'hôte",
  backupsInPlace: "Sauvegardes de l'hôte en place",
}

/** Numeric resources: label, unit, and accepted range. */
export const RESOURCE_FIELDS = {
  cpuCores: { label: 'Cœurs processeur', unit: 'cœurs', max: 512 },
  memoryGb: { label: 'Mémoire vive', unit: 'Go', max: 4096 },
  storageGb: { label: 'Stockage disponible', unit: 'Go', max: 100_000 },
  bandwidthMbps: { label: 'Débit réseau', unit: 'Mb/s', max: 100_000 },
} as const

/** The questionnaire can be edited only before the application is submitted. */
export function canEditTechnical(application: HospitalApplication | null): boolean {
  return application?.status === 'draft'
}

const yesNo = (value: boolean): YesNo => (value ? 'yes' : 'no')

export function inputFromQuestionnaire(q: TechnicalQuestionnaire): TechnicalInput {
  return {
    hostingType: q.hostingType,
    operatingSystem: q.operatingSystem,
    cpuCores: String(q.cpuCores),
    memoryGb: String(q.memoryGb),
    storageGb: String(q.storageGb),
    bandwidthMbps: String(q.bandwidthMbps),
    network: q.network,
    dmzAvailable: yesNo(q.dmzAvailable),
    outboundHttpsAllowed: yesNo(q.outboundHttpsAllowed),
    containerRuntimeAvailable: yesNo(q.containerRuntimeAvailable),
    backupsInPlace: yesNo(q.backupsInPlace),
  }
}

export const EMPTY_TECHNICAL: TechnicalInput = {
  hostingType: '',
  operatingSystem: '',
  cpuCores: '',
  memoryGb: '',
  storageGb: '',
  bandwidthMbps: '',
  network: '',
  dmzAvailable: '',
  outboundHttpsAllowed: '',
  containerRuntimeAvailable: '',
  backupsInPlace: '',
}

export function technicalInputFrom(application: HospitalApplication | null): TechnicalInput {
  const questionnaire = application?.technicalQuestionnaire
  return questionnaire ? inputFromQuestionnaire(questionnaire) : EMPTY_TECHNICAL
}

/** The canonical fictional Cap Azur answers (HC-005 fixtures), for demonstrations. */
export function demoTechnicalInput(): TechnicalInput {
  const applications = governanceFixtures.hospitalApplications as unknown as HospitalApplication[]
  const questionnaire = applications.find((a) => a.organizationId === DEMO_ORGANIZATION_ID)!.technicalQuestionnaire!
  return inputFromQuestionnaire(questionnaire)
}

/** Validates every answer. Pure. */
export function validateTechnical(input: TechnicalInput): TechnicalErrors {
  const errors: TechnicalErrors = {}
  if (input.hostingType === '') errors.hostingType = "Choisissez le type d'hébergement."
  if (input.operatingSystem.trim() === '') errors.operatingSystem = "Indiquez le système d'exploitation."
  for (const [field, spec] of Object.entries(RESOURCE_FIELDS) as [keyof typeof RESOURCE_FIELDS, (typeof RESOURCE_FIELDS)[keyof typeof RESOURCE_FIELDS]][]) {
    const value = input[field].trim()
    if (!/^\d+$/.test(value) || Number(value) < 1 || Number(value) > spec.max) {
      errors[field] = `Indiquez un nombre entier entre 1 et ${spec.max.toLocaleString('fr-FR')}.`
    }
  }
  if (input.network.trim().length < 5) errors.network = 'Décrivez brièvement le réseau (lien, segmentation).'
  for (const field of YES_NO_FIELDS) {
    if (input[field] === '') errors[field] = 'Répondez par oui ou non.'
  }
  return errors
}

/**
 * Converts valid answers to a questionnaire, keeping the DMI / HIS answers
 * (HC-056) already present. Call only when `validateTechnical` returns no error.
 */
export function toQuestionnaire(
  input: TechnicalInput,
  technicalContactId: string,
  previous: TechnicalQuestionnaire | null,
): TechnicalQuestionnaire {
  return {
    hostingType: input.hostingType as HostingType,
    operatingSystem: input.operatingSystem.trim(),
    cpuCores: Number(input.cpuCores),
    memoryGb: Number(input.memoryGb),
    storageGb: Number(input.storageGb),
    bandwidthMbps: Number(input.bandwidthMbps),
    network: input.network.trim(),
    dmzAvailable: input.dmzAvailable === 'yes',
    outboundHttpsAllowed: input.outboundHttpsAllowed === 'yes',
    containerRuntimeAvailable: input.containerRuntimeAvailable === 'yes',
    backupsInPlace: input.backupsInPlace === 'yes',
    technicalContactId,
    ...(previous?.dmiSystem !== undefined && { dmiSystem: previous.dmiSystem }),
    ...(previous?.database !== undefined && { database: previous.database }),
  }
}

export type TechnicalSaveResult =
  | { kind: 'saved'; questionnaire: TechnicalQuestionnaire }
  | { kind: 'rejected'; errors: TechnicalErrors }

export interface SaveOptions {
  simulateFailure?: boolean
  delayMs?: number
}

/** Simulated save: re-validates, as a server would. */
export async function saveTechnical(
  input: TechnicalInput,
  technicalContactId: string,
  previous: TechnicalQuestionnaire | null,
  { simulateFailure = false, delayMs = 600 }: SaveOptions = {},
): Promise<TechnicalSaveResult> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("Le service d'adhésion simulé n'a pas enregistré le questionnaire (scénario de démonstration).")
  }
  const errors = validateTechnical(input)
  if (Object.keys(errors).length > 0) return { kind: 'rejected', errors }
  return { kind: 'saved', questionnaire: toQuestionnaire(input, technicalContactId, previous) }
}

/** Returns the snapshot with the saved questionnaire on the draft application. Pure. */
export function applyTechnical(snapshot: OnboardingSnapshot, questionnaire: TechnicalQuestionnaire): OnboardingSnapshot {
  if (!canEditTechnical(snapshot.application)) {
    throw new Error('Le questionnaire ne peut être modifié que sur une inscription en brouillon.')
  }
  const application = { ...snapshot.application!, technicalQuestionnaire: questionnaire }
  return { ...snapshot, application, steps: deriveSteps(snapshot.organization, application) }
}
