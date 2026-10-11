import peopleFixtures from '../../../../../demo-data/people.json'
import { HOSPITAL_ID } from './hospital'

/**
 * MOCKED staff management: reads the fictional clinicians of the hospital and
 * keeps every change in browser memory. No API, account, or access right is created.
 */

export type StaffRole = 'physician' | 'nurse' | 'administrative'
export type StaffStatus = 'active' | 'inactive'

export interface StaffMember {
  id: string
  title: string | null
  firstName: string
  lastName: string
  role: StaffRole
  /** Specialty or service. */
  specialty: string
  status: StaffStatus
}

export interface StaffInput {
  title: string
  firstName: string
  lastName: string
  role: StaffRole | ''
  specialty: string
}

export type StaffErrors = Partial<Record<keyof StaffInput, string>>

export const ROLE_LABELS: Record<StaffRole, string> = {
  physician: 'Médecin',
  nurse: 'Infirmier·ère',
  administrative: 'Administratif',
}

export const EMPTY_STAFF_INPUT: StaffInput = { title: '', firstName: '', lastName: '', role: '', specialty: '' }

const KNOWN_ROLES: readonly string[] = Object.keys(ROLE_LABELS)

export function loadStaff(): StaffMember[] {
  return peopleFixtures.clinicians
    .filter((c) => c.organizationId === HOSPITAL_ID && KNOWN_ROLES.includes(c.role))
    .map((c) => ({
      id: c.id,
      title: c.title,
      firstName: c.firstName,
      lastName: c.lastName,
      role: c.role as StaffRole,
      specialty: c.specialty,
      status: 'active',
    }))
}

export function validateStaff(input: StaffInput): StaffErrors {
  const errors: StaffErrors = {}
  if (!input.firstName.trim()) errors.firstName = 'Indiquez le prénom.'
  if (!input.lastName.trim()) errors.lastName = 'Indiquez le nom.'
  if (!input.role) errors.role = 'Choisissez un rôle.'
  if (!input.specialty.trim()) errors.specialty = 'Indiquez la spécialité ou le service.'
  return errors
}

/** Adds a member in memory; throws if the input is invalid. */
export function addStaff(staff: readonly StaffMember[], input: StaffInput): StaffMember[] {
  if (Object.keys(validateStaff(input)).length > 0 || !input.role) throw new Error('Membre du personnel invalide.')
  const next = staff.filter((s) => s.id.startsWith('staff-local-')).length + 1
  const member: StaffMember = {
    id: `staff-local-${next}`,
    title: input.title.trim() || null,
    firstName: input.firstName.trim(),
    lastName: input.lastName.trim(),
    role: input.role,
    specialty: input.specialty.trim(),
    status: 'active',
  }
  return [...staff, member]
}

export function setStaffStatus(staff: readonly StaffMember[], id: string, status: StaffStatus): StaffMember[] {
  return staff.map((s) => (s.id === id ? { ...s, status } : s))
}

export function staffDisplayName(member: Pick<StaffMember, 'title' | 'firstName' | 'lastName'>): string {
  return [member.title, member.firstName, member.lastName].filter(Boolean).join(' ')
}

export function filterStaff(staff: readonly StaffMember[], query: string, role: StaffRole | ''): StaffMember[] {
  const q = query.trim().toLowerCase()
  return staff.filter(
    (s) =>
      (!role || s.role === role) &&
      (!q || `${staffDisplayName(s)} ${s.specialty}`.toLowerCase().includes(q)),
  )
}
