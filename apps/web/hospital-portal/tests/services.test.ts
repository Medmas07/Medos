import { describe, expect, it } from 'vitest'
import { HOSPITAL, HOSPITAL_ID } from '../src/services/hospital'
import {
  addPatient,
  ageOn,
  EMPTY_PATIENT_INPUT,
  filterPatients,
  loadPatients,
  nextLocalId,
  validatePatient,
} from '../src/services/patientService'
import {
  addStaff,
  EMPTY_STAFF_INPUT,
  filterStaff,
  loadStaff,
  setStaffStatus,
  validateStaff,
} from '../src/services/staffService'

describe('hospital', () => {
  it('is the fictional Hôpital Universitaire Bab Ennour', () => {
    expect(HOSPITAL.id).toBe(HOSPITAL_ID)
    expect(HOSPITAL.name).toBe('Hôpital Universitaire Bab Ennour')
  })
})

describe('staff', () => {
  it('loads only the clinicians of this hospital', () => {
    expect(loadStaff().map((s) => s.id)).toEqual(['clin-x', 'clin-rania', 'clin-mariem'])
  })

  it('requires names, role and specialty', () => {
    expect(Object.keys(validateStaff(EMPTY_STAFF_INPUT)).sort()).toEqual(['firstName', 'lastName', 'role', 'specialty'])
  })

  it('adds an active member with a local id and an optional title', () => {
    const staff = addStaff(loadStaff(), { title: ' ', firstName: ' Amel ', lastName: 'Trabelsi', role: 'administrative', specialty: 'Accueil' })
    expect(staff.at(-1)).toEqual({
      id: 'staff-local-1',
      title: null,
      firstName: 'Amel',
      lastName: 'Trabelsi',
      role: 'administrative',
      specialty: 'Accueil',
      status: 'active',
    })
    expect(() => addStaff(staff, EMPTY_STAFF_INPUT)).toThrow()
  })

  it('deactivates and filters by role and text', () => {
    const staff = setStaffStatus(loadStaff(), 'clin-x', 'inactive')
    expect(staff.find((s) => s.id === 'clin-x')?.status).toBe('inactive')
    expect(filterStaff(staff, '', 'nurse').map((s) => s.id)).toEqual(['clin-mariem'])
    expect(filterStaff(staff, 'urgence', '').map((s) => s.id)).toEqual(['clin-rania'])
  })
})

describe('patients', () => {
  it('loads the patients known to this hospital with its local identifier', () => {
    expect(loadPatients().map((p) => [p.id, p.localId])).toEqual([
      ['pat-a', 'BEN-2024-08812'],
      ['pat-b', 'BEN-2025-11407'],
    ])
  })

  it('exposes administrative identity only', () => {
    for (const patient of loadPatients()) {
      expect(Object.keys(patient).sort()).toEqual(['birthDate', 'city', 'firstName', 'id', 'lastName', 'localId', 'sex'])
    }
  })

  it('validates required fields and the birth date', () => {
    expect(Object.keys(validatePatient(EMPTY_PATIENT_INPUT, '2026-10-11')).sort()).toEqual([
      'birthDate',
      'city',
      'firstName',
      'lastName',
      'sex',
    ])
    const base = { firstName: 'A', lastName: 'B', sex: 'female' as const, city: 'Tunis' }
    expect(validatePatient({ ...base, birthDate: '2026-02-30' }, '2026-10-11').birthDate).toBe('Date invalide.')
    expect(validatePatient({ ...base, birthDate: '2027-01-01' }, '2026-10-11').birthDate).toMatch(/futur/)
    expect(validatePatient({ ...base, birthDate: '1990-05-01' }, '2026-10-11')).toEqual({})
  })

  it('assigns the next local id of the year', () => {
    const today = '2026-10-11'
    expect(nextLocalId(loadPatients(), 2026)).toBe('BEN-2026-00001')
    const input = { firstName: 'Salma', lastName: 'Ben Ali', sex: 'female' as const, birthDate: '1990-05-01', city: 'Tunis' }
    const once = addPatient(loadPatients(), input, today)
    const twice = addPatient(once, input, today)
    expect(twice.slice(-2).map((p) => p.localId)).toEqual(['BEN-2026-00001', 'BEN-2026-00002'])
    expect(() => addPatient(twice, EMPTY_PATIENT_INPUT, today)).toThrow()
  })

  it('computes age and searches by id, name or city', () => {
    expect(ageOn('1968-04-17', '2026-04-16')).toBe(57)
    expect(ageOn('1968-04-17', '2026-04-17')).toBe(58)
    expect(filterPatients(loadPatients(), 'ariana').map((p) => p.id)).toEqual(['pat-b'])
    expect(filterPatients(loadPatients(), 'BEN-2024-08812').map((p) => p.id)).toEqual(['pat-a'])
  })
})
