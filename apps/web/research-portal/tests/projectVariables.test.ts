import { describe, expect, it } from 'vitest'
import { createResearchProject } from '../src/services/projectCreation'
import {
  catalogEntries,
  draftFromProject,
  requestedVariables,
  saveVariables,
  validateVariablesDraft,
  VARIABLE_CATALOG,
  variablesStatus,
  type VariablesDraft,
} from '../src/services/projectVariables'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot } from '../src/services/researchService'
import type { ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const DRAFT: VariablesDraft = {
  names: ['hba1c', 'age_band', 'type_2_diabetes'],
  justification: "  L'HbA1c   par tranche d'âge mesure le contrôle glycémique des diabétiques.  ",
}

const EMPTY: VariablesDraft = { names: [], justification: '' }

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

describe('Requested variables definition (HC-095, MOCKED)', () => {
  it('offers only names the HC-180 execution contract accepts, once each', () => {
    const names = VARIABLE_CATALOG.map((v) => v.name)
    expect(new Set(names).size).toBe(names.length)
    for (const name of names) expect(name).toMatch(/^[a-z][a-z0-9_]{0,99}$/)
    expect(names).toEqual(expect.arrayContaining(['age_band', 'hba1c']))
  })

  it('accepts one to ten catalog variables with a justification', () => {
    expect(validateVariablesDraft(DRAFT)).toEqual({})
    expect(validateVariablesDraft({ ...DRAFT, names: ['sex'] })).toEqual({})
    expect(validateVariablesDraft({ ...DRAFT, names: VARIABLE_CATALOG.slice(0, 10).map((v) => v.name) })).toEqual({})
  })

  it('refuses no variable, unknown or too many variables, and a missing justification', () => {
    expect(validateVariablesDraft(EMPTY)).toEqual({
      names: 'Sélectionnez au moins une variable.',
      justification: 'La justification est obligatoire.',
    })
    expect(validateVariablesDraft({ ...DRAFT, names: ['patient_name'] }).names).toContain('catalogue')
    expect(validateVariablesDraft({ ...DRAFT, names: VARIABLE_CATALOG.map((v) => v.name) }).names).toContain('au plus 10')
    expect(validateVariablesDraft({ ...DRAFT, justification: 'Nécessaire.' }).justification).toContain('au moins 20')
    expect(validateVariablesDraft({ ...DRAFT, justification: 'a'.repeat(501) }).justification).toContain('500')
  })

  it('keeps a selection in catalog order without duplicates', () => {
    expect(catalogEntries(['hba1c', 'age_band', 'hba1c']).map((v) => v.name)).toEqual(['age_band', 'hba1c'])
  })

  it('matches fixture variables to the catalog by label and reports them as listed', async () => {
    const snapshot = await withDraft()
    const fixture = projectOf(snapshot, 'proj-001').project
    // In the fixture's own order.
    expect(requestedVariables(fixture).entries.map((v) => v.name)).toEqual([
      'age_band',
      'sex',
      'hba1c',
      'treated_hypertension',
    ])
    expect(requestedVariables(projectOf(snapshot, 'proj-002').project).unmatched).toEqual([])
    expect(requestedVariables({ ...fixture, variables: ['HbA1c', 'Revenu du foyer'] }).unmatched).toEqual([
      'Revenu du foyer',
    ])
    expect(variablesStatus(fixture)).toBe('listed')
    expect(variablesStatus(projectOf(snapshot, 'proj-003').project)).toBe('missing')
    expect(draftFromProject(projectOf(snapshot, 'proj-003').project)).toEqual(EMPTY)
  })

  it('saves the variables on the draft and updates the page summary, leaving the snapshot untouched', async () => {
    const snapshot = await withDraft()
    expect(snapshot.pages.find((p) => p.id === 'variables')?.detail).toBe('7 variables demandée(s).')

    const next = await saveVariables(snapshot, 'proj-003', DRAFT, { delayMs: 0 })
    const { project } = projectOf(next, 'proj-003')

    expect(project.variableNames).toEqual(['age_band', 'type_2_diabetes', 'hba1c'])
    expect(project.variables).toEqual(["Tranche d'âge", 'Diabète de type 2', 'HbA1c'])
    expect(project.variablesJustification).toBe("L'HbA1c par tranche d'âge mesure le contrôle glycémique des diabétiques.")
    expect(variablesStatus(project)).toBe('justified')
    expect(draftFromProject(project)).toEqual({
      names: ['age_band', 'type_2_diabetes', 'hba1c'],
      justification: project.variablesJustification,
    })
    expect(next.pages.find((p) => p.id === 'variables')?.detail).toBe('10 variables demandée(s).')
    expect(projectOf(snapshot, 'proj-003').project.variables).toEqual([])
    // Requesting variables requests no data access.
    expect(projectOf(next, 'proj-003')).toMatchObject({ request: null, authorized: false })
    for (const id of ['workspace', 'execution', 'results']) {
      expect(next.pages.find((p) => p.id === id)?.status).toBe(snapshot.pages.find((p) => p.id === id)?.status)
    }
  })

  it('refuses an invalid selection and a project whose access request is submitted', async () => {
    const snapshot = await withDraft()
    await expect(saveVariables(snapshot, 'proj-003', EMPTY, { delayMs: 0 })).rejects.toThrow('incomplète')
    await expect(saveVariables(snapshot, 'proj-001', DRAFT, { delayMs: 0 })).rejects.toThrow('ne peut plus être modifié')
    await expect(saveVariables(snapshot, 'proj-002', DRAFT, { delayMs: 0 })).rejects.toThrow('ne peut plus être modifié')
    await expect(saveVariables(snapshot, 'proj-999', DRAFT, { delayMs: 0 })).rejects.toThrow('Projet inconnu')
  })
})
