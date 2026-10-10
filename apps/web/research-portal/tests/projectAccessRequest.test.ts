import { describe, expect, it } from 'vitest'
import { deriveDashboard } from '../src/services/dashboard'
import {
  isReady,
  nextRequestId,
  readinessChecks,
  submitAccessRequest,
  validateSubmission,
} from '../src/services/projectAccessRequest'
import { createResearchProject, isEditableDraft } from '../src/services/projectCreation'
import { applyDocumentUpload } from '../src/services/projectDocuments'
import { saveHospitals } from '../src/services/projectHospitals'
import { savePopulation } from '../src/services/projectPopulation'
import { saveVariables } from '../src/services/projectVariables'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot, type DemoScenario } from '../src/services/researchService'
import type { ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')
const SUBMITTED_AT = new Date('2026-10-10T14:30:00+01:00')
const OK = { acknowledged: true }

/** A snapshot with a new draft, `proj-003`, first. */
async function withDraft(scenario: DemoScenario = 'nominal'): Promise<ResearchSnapshot> {
  const snapshot = await loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: NOW, scenario })
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

/** `proj-003` completed through the HC-093 to HC-096 steps. */
async function withCompleteDraft(scenario: DemoScenario = 'nominal'): Promise<ResearchSnapshot> {
  let snapshot = applyDocumentUpload(await withDraft(scenario), 'proj-003', 'protocol', {
    fileName: 'Protocole_IRC.pdf',
    sizeBytes: 120_000,
    mediaType: 'application/pdf',
    uploadedAt: NOW.toISOString(),
  })
  snapshot = await savePopulation(
    snapshot,
    'proj-003',
    { description: 'Adultes diabétiques suivis en consultation.', ageMin: '18', ageMax: '', encounterFrom: '', encounterTo: '' },
    { delayMs: 0 },
  )
  snapshot = await saveVariables(
    snapshot,
    'proj-003',
    { names: ['age_band', 'hba1c'], justification: "L'HbA1c par tranche d'âge décrit le contrôle glycémique." },
    { delayMs: 0 },
  )
  return saveHospitals(snapshot, 'proj-003', { organizationIds: ['org-hospital-a'] }, { delayMs: 0 })
}

const projectOf = (snapshot: ResearchSnapshot, id: string) => snapshot.projects.find((s) => s.project.id === id)!

describe('Research data-access request submission (HC-097, MOCKED)', () => {
  it('lists what a new draft still lacks, each with the page that completes it', async () => {
    const checks = readinessChecks(projectOf(await withDraft(), 'proj-003'))
    expect(checks.map((c) => [c.id, c.ready, c.page])).toEqual([
      ['protocol', false, 'protocol'],
      ['population', false, 'population'],
      ['variables', false, 'variables'],
      ['hospitals', false, 'hospitals'],
    ])
    expect(validateSubmission(projectOf(await withDraft(), 'proj-003'), { acknowledged: false })).toEqual({
      checks:
        "Complétez d'abord : protocole de recherche, population étudiée, variables demandées, établissements participants.",
      acknowledged: 'Confirmez avoir pris connaissance des conditions de la demande.',
    })
  })

  it('is ready once the HC-093 to HC-096 steps are complete', async () => {
    const summary = projectOf(await withCompleteDraft(), 'proj-003')
    expect(readinessChecks(summary).every((c) => c.ready)).toBe(true)
    expect(isReady(summary)).toBe(true)
    expect(validateSubmission(summary, OK)).toEqual({})
    expect(validateSubmission(summary, { acknowledged: false })).toHaveProperty('acknowledged')
  })

  it('requires structured population criteria and justified variables, not fixture-style text alone', async () => {
    const summary = projectOf(await withCompleteDraft(), 'proj-003')
    const textOnly = {
      ...summary.project,
      populationCriteria: undefined,
      variableNames: undefined,
      variablesJustification: undefined,
    }
    expect(readinessChecks({ project: textOnly }).filter((c) => !c.ready).map((c) => c.id)).toEqual([
      'population',
      'variables',
    ])
  })

  it('numbers requests after the fixture ones', () => {
    expect(nextRequestId([{ id: 'rar-001' }, { id: 'rar-002' }])).toBe('rar-003')
    expect(nextRequestId([])).toBe('rar-001')
  })

  it('submits the request under review, locks the project, and authorizes nothing', async () => {
    const snapshot = await withCompleteDraft()
    const { request, snapshot: next } = await submitAccessRequest(snapshot, 'proj-003', OK, {
      delayMs: 0,
      now: SUBMITTED_AT,
    })

    expect(request).toEqual({
      id: 'rar-003',
      projectId: 'proj-003',
      submittedById: DEMO_RESEARCHER_ID,
      submittedAt: SUBMITTED_AT.toISOString(),
      status: 'under_review',
      decisionId: null,
    })
    const summary = projectOf(next, 'proj-003')
    expect(summary).toMatchObject({ request, decision: null, authorized: false })
    expect(summary.project).toMatchObject({ status: 'under_review', researchAccessRequestId: 'rar-003' })
    expect(isEditableDraft(summary)).toBe(false)
    expect(next.pages.find((p) => p.id === 'submit-request')?.detail).toBe(
      "3 demandes soumise(s) à l'Autorité de gouvernance.",
    )
    for (const id of ['workspace', 'execution', 'results']) {
      expect(next.pages.find((p) => p.id === id)?.status).toBe(snapshot.pages.find((p) => p.id === id)?.status)
    }
    // The dashboard now waits for the Governance decision.
    const project = deriveDashboard(next).projects.find((p) => p.summary.project.id === 'proj-003')
    expect(project?.next.kind).toBe('await_decision')
    // The previous snapshot is untouched.
    expect(projectOf(snapshot, 'proj-003').request).toBeNull()
  })

  it('keeps fixture identifiers reserved in the empty scenario', async () => {
    const { request } = await submitAccessRequest(await withCompleteDraft('empty'), 'proj-003', OK, { delayMs: 0 })
    expect(request.id).toBe('rar-003')
  })

  it('refuses an incomplete project, a missing acknowledgement, and a project already submitted', async () => {
    await expect(submitAccessRequest(await withDraft(), 'proj-003', OK, { delayMs: 0 })).rejects.toThrow('incomplète')
    const complete = await withCompleteDraft()
    await expect(submitAccessRequest(complete, 'proj-003', { acknowledged: false }, { delayMs: 0 })).rejects.toThrow(
      'incomplète',
    )
    await expect(submitAccessRequest(complete, 'proj-002', OK, { delayMs: 0 })).rejects.toThrow('ne peut plus être modifié')
    const { snapshot } = await submitAccessRequest(complete, 'proj-003', OK, { delayMs: 0 })
    await expect(submitAccessRequest(snapshot, 'proj-003', OK, { delayMs: 0 })).rejects.toThrow('ne peut plus être modifié')
  })
})
