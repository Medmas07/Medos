import peopleFixtures from '../../../../../demo-data/people.json'
import type { OnboardingSnapshot, Organization, StaffMember } from '../types/onboarding'
import { deriveSteps, DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, listOrganizations } from './onboardingService'

/**
 * MOCKED hospital registration (HC-051). Validation runs in the browser, and
 * submission is simulated with a deterministic delay. No account is created and
 * nothing leaves the browser. Registering never approves: the Governance / Ethics
 * Authority decides later. A registration submission contract is PLANNED.
 */

export type OrganizationType = 'hospital' | 'private_practice'

export interface RegistrationInput {
  organizationName: string
  shortName: string
  organizationType: OrganizationType | ''
  city: string
  managerFirstName: string
  managerLastName: string
  managerEmail: string
  managerPhone: string
  attestsAccuracy: boolean
  acknowledgesGovernance: boolean
}

export type RegistrationField = keyof RegistrationInput
export type RegistrationErrors = Partial<Record<RegistrationField, string>>

export const EMPTY_REGISTRATION: RegistrationInput = {
  organizationName: '',
  shortName: '',
  organizationType: '',
  city: '',
  managerFirstName: '',
  managerLastName: '',
  managerEmail: '',
  managerPhone: '',
  attestsAccuracy: false,
  acknowledgesGovernance: false,
}

export const ORGANIZATION_TYPE_LABELS: Record<OrganizationType, string> = {
  hospital: 'Établissement hospitalier',
  private_practice: 'Cabinet médical',
}

export interface RegistrationStep {
  id: 'organization' | 'manager' | 'confirmation'
  label: string
  fields: readonly RegistrationField[]
}

export const REGISTRATION_STEPS: readonly RegistrationStep[] = [
  { id: 'organization', label: 'Établissement', fields: ['organizationName', 'shortName', 'organizationType', 'city'] },
  {
    id: 'manager',
    label: 'Responsable',
    fields: ['managerFirstName', 'managerLastName', 'managerEmail', 'managerPhone'],
  },
  { id: 'confirmation', label: 'Vérification et envoi', fields: ['attestsAccuracy', 'acknowledgesGovernance'] },
]

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PHONE_PATTERN = /^\+?[0-9 ]{8,20}$/

function checkField(field: RegistrationField, input: RegistrationInput): string | undefined {
  const value = input[field]
  switch (field) {
    case 'organizationName':
      return input.organizationName.trim().length < 3 ? "Indiquez le nom officiel de l'établissement." : undefined
    case 'shortName':
      return input.shortName.trim() === '' ? 'Indiquez un nom court.' : undefined
    case 'organizationType':
      return input.organizationType === '' ? "Choisissez le type d'établissement." : undefined
    case 'city':
      return input.city.trim() === '' ? 'Indiquez la ville.' : undefined
    case 'managerFirstName':
      return input.managerFirstName.trim() === '' ? 'Indiquez le prénom.' : undefined
    case 'managerLastName':
      return input.managerLastName.trim() === '' ? 'Indiquez le nom.' : undefined
    case 'managerEmail':
      return EMAIL_PATTERN.test(input.managerEmail.trim()) ? undefined : 'Indiquez une adresse e-mail valide.'
    case 'managerPhone':
      return PHONE_PATTERN.test(input.managerPhone.trim()) ? undefined : 'Indiquez un numéro de téléphone valide.'
    case 'attestsAccuracy':
    case 'acknowledgesGovernance':
      return value ? undefined : 'Cette confirmation est obligatoire.'
  }
}

/** Validates the given fields (all fields by default). Pure. */
export function validateRegistration(
  input: RegistrationInput,
  fields: readonly RegistrationField[] = REGISTRATION_STEPS.flatMap((s) => s.fields),
): RegistrationErrors {
  const errors: RegistrationErrors = {}
  for (const field of fields) {
    const message = checkField(field, input)
    if (message) errors[field] = message
  }
  return errors
}

/** Index of the first form step holding one of the errors, or -1. */
export function firstStepWithError(errors: RegistrationErrors): number {
  return REGISTRATION_STEPS.findIndex((step) => step.fields.some((f) => errors[f]))
}

function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
}

/** The canonical fictional Cap Azur registration, for demonstrations. */
export function demoRegistrationInput(): RegistrationInput {
  const organization = listOrganizations().find((o) => o.id === DEMO_ORGANIZATION_ID)!
  const manager = (peopleFixtures.staff as unknown as StaffMember[]).find((p) => p.id === DEMO_MANAGER_ID)!
  return {
    organizationName: organization.name,
    shortName: organization.shortName,
    organizationType: 'hospital',
    city: organization.city,
    managerFirstName: manager.firstName,
    managerLastName: manager.lastName,
    // Reserved `.example` domain and a placeholder number: fictional contact data.
    managerEmail: 'mehdi.sassi@cap-azur.example',
    managerPhone: '+216 70 000 000',
    attestsAccuracy: true,
    acknowledgesGovernance: true,
  }
}

export interface RegistrationReceipt {
  reference: string
  submittedAt: string
}

export type SubmissionResult =
  | { kind: 'accepted'; receipt: RegistrationReceipt }
  | { kind: 'rejected'; errors: RegistrationErrors }

export interface SubmitOptions {
  /** Simulates an unavailable service (demo scenario). */
  simulateFailure?: boolean
  delayMs?: number
  now?: Date
}

/**
 * Simulated submission. Re-validates everything and rejects an establishment
 * whose name is already registered in the fictional registry, as a server would.
 */
export async function submitRegistration(
  input: RegistrationInput,
  { simulateFailure = false, delayMs = 800, now = new Date() }: SubmitOptions = {},
): Promise<SubmissionResult> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("Le service d'inscription simulé n'a pas répondu (scénario de démonstration).")
  }

  const errors = validateRegistration(input)
  const name = normalize(input.organizationName)
  const duplicate = listOrganizations().some((o) => o.id !== DEMO_ORGANIZATION_ID && normalize(o.name) === name)
  if (duplicate) errors.organizationName = 'Cet établissement est déjà enregistré dans l’écosystème.'
  if (Object.keys(errors).length > 0) return { kind: 'rejected', errors }

  const date = now.toISOString().slice(0, 10).replaceAll('-', '')
  const suffix = normalize(input.shortName).toUpperCase().slice(0, 12)
  return { kind: 'accepted', receipt: { reference: `REG-${date}-${suffix}`, submittedAt: now.toISOString() } }
}

/**
 * Returns the snapshot after a local registration: the organization and its
 * manager take the submitted values, and a `draft` application is created. Pure.
 */
export function applyRegistration(
  snapshot: OnboardingSnapshot,
  input: RegistrationInput,
  receipt: RegistrationReceipt,
): OnboardingSnapshot {
  const organization: Organization = {
    ...snapshot.organization,
    name: input.organizationName.trim(),
    shortName: input.shortName.trim(),
    type: input.organizationType,
    city: input.city.trim(),
  }
  const manager: StaffMember = {
    ...snapshot.manager,
    firstName: input.managerFirstName.trim(),
    lastName: input.managerLastName.trim(),
    email: input.managerEmail.trim(),
    phone: input.managerPhone.trim(),
  }
  const application = {
    id: receipt.reference,
    organizationId: organization.id,
    submittedById: manager.id,
    submittedAt: receipt.submittedAt,
    status: 'draft' as const,
    documents: [],
    agreements: [],
    technicalQuestionnaire: null,
    reviewSteps: [],
    decisionId: null,
  }
  return {
    ...snapshot,
    organization,
    manager,
    application,
    steps: deriveSteps(organization, application),
  }
}
