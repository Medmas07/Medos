import { describe, expect, it } from 'vitest'
import { createResearchProject } from '../src/services/projectCreation'
import {
  criteriaFromDraft,
  draftFromProject,
  populationStatus,
  savePopulation,
  validatePopulationDraft,
  type PopulationDraft,
} from '../src/services/projectPopulation'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot } from '../src/services/researchService'
import type { ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const DRAFT: PopulationDraft = {
  description: '  Adultes   diabétiques de type 2 suivis en consultation.  ',
  ageMin: '40',
  ageMax: '79',
  encounterFrom: '2024-01-01',
  encounterTo: '2026-12-31',
}

const EMPTY: PopulationDraft = { description: '', ageMin: '', ageMax: '', encounterFrom: '', encounterTo: '' }

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

describe('Research population definition (HC-094, MOCKED)', () => {
  it('accepts a described population with at least one criterion', () => {
    expect(validatePopulationDraft(DRAFT)).toEqual({})
    expect(validatePopulationDraft({ ...DRAFT, ageMax: '', encounterFrom: '', encounterTo: '' })).toEqual({})
    expect(validatePopulationDraft({ ...DRAFT, ageMin: '', ageMax: '', encounterTo: '' })).toEqual({})
  })

  it('requires a description of 20 to 500 characters and one criterion', () => {
    expect(validatePopulationDraft(EMPTY)).toEqual({
      description: 'La description de la population est obligatoire.',
      criteria: "Indiquez au moins un critère : une tranche d'âge ou une période de consultation.",
    })
    expect(validatePopulationDraft({ ...DRAFT, description: 'Adultes' }).description).toContain('au moins 20')
    expect(validatePopulationDraft({ ...DRAFT, description: 'a'.repeat(501) }).description).toContain('500')
  })

  it('refuses invalid or inverted ages and dates', () => {
    expect(validatePopulationDraft({ ...DRAFT, ageMin: '-1' }).ageMin).toContain('de 0 à 130')
    expect(validatePopulationDraft({ ...DRAFT, ageMin: '40.5' }).ageMin).toContain('années entières')
    expect(validatePopulationDraft({ ...DRAFT, ageMax: '131' }).ageMax).toContain('de 0 à 130')
    expect(validatePopulationDraft({ ...DRAFT, ageMin: '80' }).ageMax).toContain('supérieur ou égal')
    expect(validatePopulationDraft({ ...DRAFT, ageMin: '79' })).toEqual({})
    expect(validatePopulationDraft({ ...DRAFT, encounterFrom: '2026-02-30' }).encounterFrom).toBe('Date invalide.')
    expect(validatePopulationDraft({ ...DRAFT, encounterTo: '31/12/2026' }).encounterTo).toBe('Date invalide.')
    expect(validatePopulationDraft({ ...DRAFT, encounterFrom: '2027-01-01' }).encounterTo).toContain('suivre son début')
  })

  it('keeps only the set criteria, as the HC-180 execution contract expects', () => {
    expect(criteriaFromDraft(DRAFT)).toEqual({
      ageMin: 40,
      ageMax: 79,
      encounterFrom: '2024-01-01',
      encounterTo: '2026-12-31',
    })
    expect(criteriaFromDraft({ ...DRAFT, ageMin: ' ', encounterTo: '' })).toEqual({
      ageMax: 79,
      encounterFrom: '2024-01-01',
    })
    expect(criteriaFromDraft({ ...DRAFT, ageMin: '0' })).toMatchObject({ ageMin: 0 })
  })

  it('reports fixture projects as described and new drafts as missing', async () => {
    const snapshot = await withDraft()
    expect(populationStatus(projectOf(snapshot, 'proj-001').project)).toBe('described')
    expect(populationStatus(projectOf(snapshot, 'proj-003').project)).toBe('missing')
    expect(draftFromProject(projectOf(snapshot, 'proj-003').project)).toEqual(EMPTY)
  })

  it('saves the population on the draft and updates the page summary, leaving the snapshot untouched', async () => {
    const snapshot = await withDraft()
    expect(snapshot.pages.find((p) => p.id === 'population')?.detail).toBe('2 populations décrite(s).')

    const next = await savePopulation(snapshot, 'proj-003', DRAFT, { delayMs: 0 })
    const { project } = projectOf(next, 'proj-003')

    expect(project.population).toBe('Adultes diabétiques de type 2 suivis en consultation.')
    expect(project.populationCriteria).toEqual(criteriaFromDraft(DRAFT))
    expect(populationStatus(project)).toBe('defined')
    expect(draftFromProject(project)).toEqual({ ...DRAFT, description: project.population })
    expect(next.pages.find((p) => p.id === 'population')?.detail).toBe('3 populations décrite(s).')
    expect(projectOf(snapshot, 'proj-003').project.population).toBe('')
    // A population requests no data access.
    expect(projectOf(next, 'proj-003')).toMatchObject({ request: null, authorized: false })
    for (const id of ['workspace', 'execution', 'results']) {
      expect(next.pages.find((p) => p.id === id)?.status).toBe(snapshot.pages.find((p) => p.id === id)?.status)
    }
  })

  it('refuses an invalid population and a project whose access request is submitted', async () => {
    const snapshot = await withDraft()
    await expect(savePopulation(snapshot, 'proj-003', EMPTY, { delayMs: 0 })).rejects.toThrow('incomplète')
    await expect(savePopulation(snapshot, 'proj-001', DRAFT, { delayMs: 0 })).rejects.toThrow('ne peut plus être modifié')
    await expect(savePopulation(snapshot, 'proj-002', DRAFT, { delayMs: 0 })).rejects.toThrow('ne peut plus être modifié')
    await expect(savePopulation(snapshot, 'proj-999', DRAFT, { delayMs: 0 })).rejects.toThrow('Projet inconnu')
  })
})
