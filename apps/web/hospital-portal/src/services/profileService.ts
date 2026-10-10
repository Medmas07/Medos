import governanceFixtures from '../../../../../demo-data/governance.json'
import type { AdministrativeProfile, HospitalApplication, OnboardingSnapshot } from '../types/onboarding'
import { deriveSteps, DEMO_ORGANIZATION_ID } from './onboardingService'
import { EMAIL_PATTERN, PHONE_PATTERN } from './registrationService'

/**
 * MOCKED organization profile (HC-052). The administrative profile is edited in
 * the browser and "saved" by a simulated service with a deterministic delay; it
 * is kept in memory only. An administrative-profile contract is PLANNED.
 */

/** Form values, all as strings; converted to an `AdministrativeProfile` on save. */
export interface ProfileInput {
  legalName: string
  legalStatus: AdministrativeProfile['legalStatus'] | ''
  registrationNumber: string
  bedCapacity: string
  street: string
  postalCode: string
  city: string
  governorate: string
  phone: string
  email: string
  representativeName: string
  representativeRole: string
  dpoName: string
  dpoEmail: string
  securityName: string
  securityEmail: string
}

export type ProfileField = keyof ProfileInput
export type ProfileErrors = Partial<Record<ProfileField, string>>

export const LEGAL_STATUS_LABELS: Record<AdministrativeProfile['legalStatus'], string> = {
  public: 'Établissement public de santé',
  private: 'Établissement privé',
}

/** The profile can be edited only before the application is submitted for review. */
export function canEditProfile(application: HospitalApplication | null): boolean {
  return application?.status === 'draft'
}

/** The canonical fictional Cap Azur profile (HC-005 fixtures), for demonstrations. */
export function demoProfile(): AdministrativeProfile {
  const applications = governanceFixtures.hospitalApplications as unknown as HospitalApplication[]
  return applications.find((a) => a.organizationId === DEMO_ORGANIZATION_ID)!.administrativeProfile!
}

/** Form values from the saved profile, or prefilled from the registration. */
export function profileInputFrom(snapshot: OnboardingSnapshot): ProfileInput {
  const profile = snapshot.application?.administrativeProfile
  return profile ? inputFromProfile(profile) : prefilledInput(snapshot)
}

export function inputFromProfile(profile: AdministrativeProfile): ProfileInput {
  return {
    legalName: profile.legalName,
    legalStatus: profile.legalStatus,
    registrationNumber: profile.registrationNumber,
    bedCapacity: String(profile.bedCapacity),
    street: profile.address.street,
    postalCode: profile.address.postalCode,
    city: profile.address.city,
    governorate: profile.address.governorate,
    phone: profile.phone,
    email: profile.email,
    representativeName: profile.legalRepresentative.fullName,
    representativeRole: profile.legalRepresentative.role,
    dpoName: profile.dataProtectionOfficer.fullName,
    dpoEmail: profile.dataProtectionOfficer.email,
    securityName: profile.securityContact?.fullName ?? '',
    securityEmail: profile.securityContact?.email ?? '',
  }
}

function prefilledInput(snapshot: OnboardingSnapshot): ProfileInput {
  return {
    legalName: snapshot.organization.name,
    legalStatus: '',
    registrationNumber: '',
    bedCapacity: '',
    street: '',
    postalCode: '',
    city: snapshot.organization.city,
    governorate: '',
    phone: '',
    email: '',
    representativeName: '',
    representativeRole: '',
    dpoName: '',
    dpoEmail: '',
    securityName: '',
    securityEmail: '',
  }
}

const REQUIRED: Partial<Record<ProfileField, string>> = {
  legalName: 'Indiquez la raison sociale.',
  legalStatus: 'Choisissez le statut juridique.',
  registrationNumber: "Indiquez l'identifiant administratif.",
  street: "Indiquez l'adresse.",
  city: 'Indiquez la ville.',
  governorate: 'Indiquez le gouvernorat.',
  representativeName: 'Indiquez le représentant légal.',
  representativeRole: 'Indiquez sa fonction.',
  dpoName: 'Indiquez le délégué à la protection des données.',
}

/** Validates the whole profile. The security contact is optional but must be complete if given. Pure. */
export function validateProfile(input: ProfileInput): ProfileErrors {
  const errors: ProfileErrors = {}
  for (const [field, message] of Object.entries(REQUIRED) as [ProfileField, string][]) {
    if (input[field].trim() === '') errors[field] = message
  }

  const beds = input.bedCapacity.trim()
  if (!/^\d{1,4}$/.test(beds)) errors.bedCapacity = 'Indiquez un nombre de lits (0 à 9999).'
  if (!/^\d{4}$/.test(input.postalCode.trim())) errors.postalCode = 'Le code postal comporte 4 chiffres.'
  if (!PHONE_PATTERN.test(input.phone.trim())) errors.phone = 'Indiquez un numéro de téléphone valide.'
  if (!EMAIL_PATTERN.test(input.email.trim())) errors.email = 'Indiquez une adresse e-mail valide.'
  if (!EMAIL_PATTERN.test(input.dpoEmail.trim())) errors.dpoEmail = 'Indiquez une adresse e-mail valide.'

  const securityName = input.securityName.trim()
  const securityEmail = input.securityEmail.trim()
  if (securityName !== '' || securityEmail !== '') {
    if (securityName === '') errors.securityName = 'Indiquez le nom du contact sécurité, ou laissez les deux champs vides.'
    if (!EMAIL_PATTERN.test(securityEmail)) errors.securityEmail = 'Indiquez une adresse e-mail valide.'
  }
  return errors
}

/** Converts valid form values to a profile. Call only when `validateProfile` returns no error. */
export function toProfile(input: ProfileInput, updatedAt: string): AdministrativeProfile {
  const securityName = input.securityName.trim()
  return {
    legalName: input.legalName.trim(),
    legalStatus: input.legalStatus as AdministrativeProfile['legalStatus'],
    registrationNumber: input.registrationNumber.trim(),
    bedCapacity: Number(input.bedCapacity.trim()),
    address: {
      street: input.street.trim(),
      postalCode: input.postalCode.trim(),
      city: input.city.trim(),
      governorate: input.governorate.trim(),
    },
    phone: input.phone.trim(),
    email: input.email.trim(),
    legalRepresentative: { fullName: input.representativeName.trim(), role: input.representativeRole.trim() },
    dataProtectionOfficer: { fullName: input.dpoName.trim(), email: input.dpoEmail.trim() },
    securityContact: securityName ? { fullName: securityName, email: input.securityEmail.trim() } : null,
    updatedAt,
  }
}

export type SaveResult = { kind: 'saved'; profile: AdministrativeProfile } | { kind: 'rejected'; errors: ProfileErrors }

export interface SaveOptions {
  /** Simulates an unavailable service (demo scenario). */
  simulateFailure?: boolean
  delayMs?: number
  now?: Date
}

/** Simulated save: re-validates, as a server would, then returns the stored profile. */
export async function saveProfile(
  input: ProfileInput,
  { simulateFailure = false, delayMs = 600, now = new Date() }: SaveOptions = {},
): Promise<SaveResult> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("Le service d'adhésion simulé n'a pas enregistré le profil (scénario de démonstration).")
  }
  const errors = validateProfile(input)
  if (Object.keys(errors).length > 0) return { kind: 'rejected', errors }
  return { kind: 'saved', profile: toProfile(input, now.toISOString()) }
}

/** Returns the snapshot with the saved profile on the draft application. Pure. */
export function applyProfile(snapshot: OnboardingSnapshot, profile: AdministrativeProfile): OnboardingSnapshot {
  if (!canEditProfile(snapshot.application)) {
    throw new Error('Le profil ne peut être modifié que sur une inscription en brouillon.')
  }
  const application = { ...snapshot.application!, administrativeProfile: profile }
  return { ...snapshot, application, steps: deriveSteps(snapshot.organization, application) }
}
