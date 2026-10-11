import peopleFixtures from '../../../../../demo-data/people.json'
import { HOSPITAL_ID, LOCAL_ID_PREFIX } from './hospital'

/**
 * MOCKED patient management: administrative identity only (no clinical data),
 * for the fictional patients known to the hospital. Changes stay in browser memory.
 */

export type Sex = 'female' | 'male'

export interface Patient {
  id: string
  /** The hospital's local identifier (IPP). */
  localId: string
  firstName: string
  lastName: string
  sex: Sex
  /** ISO date, YYYY-MM-DD. */
  birthDate: string
  city: string
}

export interface PatientInput {
  firstName: string
  lastName: string
  sex: Sex | ''
  birthDate: string
  city: string
}

export type PatientErrors = Partial<Record<keyof PatientInput, string>>

export const SEX_LABELS: Record<Sex, string> = { female: 'Femme', male: 'Homme' }

export const EMPTY_PATIENT_INPUT: PatientInput = { firstName: '', lastName: '', sex: '', birthDate: '', city: '' }

export function loadPatients(): Patient[] {
  return peopleFixtures.patients.flatMap((p) => {
    const local = p.localIdentifiers.find((l) => l.organizationId === HOSPITAL_ID)
    if (!local) return []
    return [
      {
        id: p.id,
        localId: local.value,
        firstName: p.firstName,
        lastName: p.lastName,
        sex: p.sex as Sex,
        birthDate: p.birthDate,
        city: p.city,
      },
    ]
  })
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

function isRealDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false
  const date = new Date(`${value}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(value)
}

export function validatePatient(input: PatientInput, today: string): PatientErrors {
  const errors: PatientErrors = {}
  if (!input.firstName.trim()) errors.firstName = 'Indiquez le prénom.'
  if (!input.lastName.trim()) errors.lastName = 'Indiquez le nom.'
  if (!input.sex) errors.sex = 'Choisissez le sexe.'
  if (!input.birthDate) errors.birthDate = 'Indiquez la date de naissance.'
  else if (!isRealDate(input.birthDate)) errors.birthDate = 'Date invalide.'
  else if (input.birthDate > today) errors.birthDate = 'La date de naissance ne peut pas être dans le futur.'
  if (!input.city.trim()) errors.city = 'Indiquez la ville.'
  return errors
}

/** Next free local identifier for the year, e.g. `BEN-2026-00001`. */
export function nextLocalId(patients: readonly Patient[], year: number): string {
  const prefix = `${LOCAL_ID_PREFIX}-${year}-`
  const highest = patients
    .filter((p) => p.localId.startsWith(prefix))
    .reduce((max, p) => Math.max(max, Number(p.localId.slice(prefix.length)) || 0), 0)
  return `${prefix}${String(highest + 1).padStart(5, '0')}`
}

/** Registers a patient in memory; throws if the input is invalid. */
export function addPatient(patients: readonly Patient[], input: PatientInput, today: string): Patient[] {
  if (Object.keys(validatePatient(input, today)).length > 0 || !input.sex) throw new Error('Patient invalide.')
  const localId = nextLocalId(patients, Number(today.slice(0, 4)))
  const patient: Patient = {
    id: `pat-local-${localId}`,
    localId,
    firstName: input.firstName.trim(),
    lastName: input.lastName.trim(),
    sex: input.sex,
    birthDate: input.birthDate,
    city: input.city.trim(),
  }
  return [...patients, patient]
}

export function ageOn(birthDate: string, today: string): number {
  const [by, bm, bd] = birthDate.split('-').map(Number)
  const [ty, tm, td] = today.split('-').map(Number)
  return ty! - by! - (tm! < bm! || (tm === bm && td! < bd!) ? 1 : 0)
}

export function filterPatients(patients: readonly Patient[], query: string): Patient[] {
  const q = query.trim().toLowerCase()
  if (!q) return [...patients]
  return patients.filter((p) => `${p.localId} ${p.firstName} ${p.lastName} ${p.city}`.toLowerCase().includes(q))
}

/** Today's date as YYYY-MM-DD in the hospital's time zone. */
export function todayIso(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Africa/Tunis' }).format(now)
}
