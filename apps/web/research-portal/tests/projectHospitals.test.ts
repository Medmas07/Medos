import { describe, expect, it } from 'vitest'
import { createResearchProject } from '../src/services/projectCreation'
import {
  draftFromProject,
  hospitalEligibility,
  hospitalsStatus,
  saveHospitals,
  selectedHospitals,
  validateHospitalsDraft,
  type HospitalsDraft,
} from '../src/services/projectHospitals'
import { DEMO_RESEARCHER_ID, HEALTHCARE_ORGANIZATIONS, loadResearchSnapshot } from '../src/services/researchService'
import type { ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const DRAFT: HospitalsDraft = { organizationIds: ['org-hospital-b', 'org-private-practice', 'org-hospital-a'] }

/** The nominal snapshot with a new draft, `proj-003`, first. */
async function withDraft(): Promise<ResearchSnapshot> {
  const snapshot = await loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: NOW })
  const created = await createResearchProject(
    snapshot,
    {
      title: 'Insuffisance rénale chronique et diabète',
      summary: "Décrire la fréquence de l'insuffisance rénale chronique chez les adultes diabétiques suivis.",
    },
    { delayMs: 0, now: NOW },
  )
  return created.snapshot
}

const projectOf = (snapshot: ResearchSnapshot, id: string) => snapshot.projects.find((s) => s.project.id === id)!
const organization = (id: string) => HEALTHCARE_ORGANIZATIONS.find((o) => o.id === id)!

describe('Participating hospitals selection (HC-096, MOCKED)', () => {
  it('offers only healthcare organizations, with their federation state', () => {
    expect(HEALTHCARE_ORGANIZATIONS.map((o) => o.id)).toEqual([
      'org-hospital-a',
      'org-hospital-b',
      'org-hospital-c',
      'org-private-practice',
    ])
    expect(hospitalEligibility(organization('org-hospital-a'))).toBe('eligible')
    // Approved, but its node is degraded and its DMI disconnected.
    expect(hospitalEligibility(organization('org-private-practice'))).toBe('degraded')
    // Onboarding under review, no Hospital Node yet.
    expect(hospitalEligibility(organization('org-hospital-c'))).toBe('not_federated')
  })

  it('accepts eligible and degraded organizations', () => {
    expect(validateHospitalsDraft(DRAFT)).toEqual({})
    expect(validateHospitalsDraft({ organizationIds: ['org-hospital-a'] })).toEqual({})
  })

  it('refuses no organization, an unknown or non-healthcare one, and one without an approved node', () => {
    expect(validateHospitalsDraft({ organizationIds: [] })).toEqual({
      organizationIds: 'Sélectionnez au moins un établissement.',
    })
    expect(validateHospitalsDraft({ organizationIds: ['org-hospital-z'] }).organizationIds).toContain('fédéré')
    expect(validateHospitalsDraft({ organizationIds: ['org-governance'] }).organizationIds).toContain('fédéré')
    expect(validateHospitalsDraft({ organizationIds: ['org-hospital-a', 'org-hospital-c'] }).organizationIds).toContain(
      'Hospital Node',
    )
  })

  it('keeps a selection in directory order without duplicates', () => {
    expect(selectedHospitals(['org-hospital-b', 'org-hospital-a', 'org-hospital-b']).map((o) => o.id)).toEqual([
      'org-hospital-a',
      'org-hospital-b',
    ])
  })

  it('reads fixture selections and reports a new draft as missing', async () => {
    const snapshot = await withDraft()
    expect(hospitalsStatus(projectOf(snapshot, 'proj-002').project)).toBe('selected')
    expect(draftFromProject(projectOf(snapshot, 'proj-002').project)).toEqual({
      organizationIds: ['org-hospital-b', 'org-private-practice'],
    })
    expect(hospitalsStatus(projectOf(snapshot, 'proj-003').project)).toBe('missing')
    expect(draftFromProject(projectOf(snapshot, 'proj-003').project)).toEqual({ organizationIds: [] })
  })

  it('saves the hospitals on the draft and updates its summary, leaving the snapshot untouched', async () => {
    const snapshot = await withDraft()
    expect(snapshot.pages.find((p) => p.id === 'hospitals')?.detail).toBe('3 établissements sollicité(s).')

    const next = await saveHospitals(snapshot, 'proj-003', DRAFT, { delayMs: 0 })
    const summary = projectOf(next, 'proj-003')

    expect(summary.project.participatingOrganizationIds).toEqual([
      'org-hospital-a',
      'org-hospital-b',
      'org-private-practice',
    ])
    // The home page and dashboard read the joined organizations.
    expect(summary.participatingOrganizations.map((o) => o.shortName)).toEqual([
      'HU Bab Ennour',
      'HR Oued Zitoun',
      'Cabinet Bouzid',
    ])
    expect(hospitalsStatus(summary.project)).toBe('selected')
    expect(projectOf(snapshot, 'proj-003').project.participatingOrganizationIds).toEqual([])
    // Selecting hospitals requests no data access.
    expect(summary).toMatchObject({ request: null, authorized: false })
    for (const id of ['workspace', 'execution', 'results']) {
      expect(next.pages.find((p) => p.id === id)?.status).toBe(snapshot.pages.find((p) => p.id === id)?.status)
    }
  })

  it('refuses an invalid selection and a project whose access request is submitted', async () => {
    const snapshot = await withDraft()
    await expect(saveHospitals(snapshot, 'proj-003', { organizationIds: [] }, { delayMs: 0 })).rejects.toThrow(
      'incomplète',
    )
    await expect(
      saveHospitals(snapshot, 'proj-003', { organizationIds: ['org-hospital-c'] }, { delayMs: 0 }),
    ).rejects.toThrow('incomplète')
    await expect(saveHospitals(snapshot, 'proj-001', DRAFT, { delayMs: 0 })).rejects.toThrow('ne peut plus être modifié')
    await expect(saveHospitals(snapshot, 'proj-999', DRAFT, { delayMs: 0 })).rejects.toThrow('Projet inconnu')
  })
})
