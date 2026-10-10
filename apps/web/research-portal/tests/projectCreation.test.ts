import { describe, expect, it } from 'vitest'
import { deriveDashboard } from '../src/services/dashboard'
import {
  createResearchProject,
  nextProjectId,
  validateProjectDraft,
  type ProjectDraft,
} from '../src/services/projectCreation'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot } from '../src/services/researchService'
import type { ResearchProject } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const load = (scenario?: 'nominal' | 'empty') =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { scenario, delayMs: 0, now: NOW })

const DRAFT: ProjectDraft = {
  title: '  Insuffisance rénale chronique   et diabète  ',
  summary: "Décrire la fréquence de l'insuffisance rénale chronique chez les adultes diabétiques suivis.",
}

const projectsOf = async () => (await load()).projects.map((s) => s.project)

describe('Research project creation (HC-092, MOCKED)', () => {
  it('accepts a complete draft', async () => {
    expect(validateProjectDraft(DRAFT, await projectsOf())).toEqual({})
  })

  it('requires a title and a scientific objective of reasonable length', async () => {
    const existing = await projectsOf()
    expect(validateProjectDraft({ title: '   ', summary: '' }, existing)).toEqual({
      title: 'Le titre est obligatoire.',
      summary: "L'objectif scientifique est obligatoire.",
    })
    const short = validateProjectDraft({ title: 'Asthme', summary: 'Trop court.' }, existing)
    expect(short.title).toContain('au moins')
    expect(short.summary).toContain('au moins')
    const long = validateProjectDraft({ title: 'x'.repeat(151), summary: 'y'.repeat(1001) }, existing)
    expect(long.title).toContain('dépasser')
    expect(long.summary).toContain('dépasser')
  })

  it("refuses a title already used by one of the researcher's projects, ignoring case and spacing", async () => {
    const existing = await projectsOf()
    const duplicate = { ...DRAFT, title: ` ${existing[0].title.toUpperCase()} ` }
    expect(validateProjectDraft(duplicate, existing).title).toBe('Un de vos projets porte déjà ce titre.')
  })

  it('numbers projects after the highest existing identifier', () => {
    const ids = (...values: string[]) => values.map((id) => ({ id }) as ResearchProject)
    expect(nextProjectId([])).toBe('proj-001')
    expect(nextProjectId(ids('proj-001', 'proj-007', 'other'))).toBe('proj-008')
  })

  it("creates a draft owned by the signed-in researcher, first in the researcher's projects", async () => {
    const snapshot = await load()
    const { project, snapshot: next } = await createResearchProject(snapshot, DRAFT, { delayMs: 0, now: NOW })

    expect(project).toMatchObject({
      id: 'proj-003',
      title: 'Insuffisance rénale chronique et diabète',
      principalInvestigatorId: DEMO_RESEARCHER_ID,
      organizationId: 'org-research-lab',
      status: 'draft',
      createdAt: NOW.toISOString(),
      variables: [],
      participatingOrganizationIds: [],
      protocolDocument: null,
      researchAccessRequestId: null,
    })
    expect(next.projects.map((s) => s.project.id)).toEqual(['proj-003', 'proj-002', 'proj-001'])
    expect(next.projects[0]).toMatchObject({ request: null, decision: null, authorized: false })
    expect(next.pages.find((p) => p.id === 'dashboard')?.detail).toBe('3 projets de recherche.')
    // The original snapshot is left untouched.
    expect(snapshot.projects).toHaveLength(2)
  })

  it('requests no data access: the draft unlocks no Compute-to-Data page and awaits its access request', async () => {
    const empty = await load('empty')
    const { project, snapshot } = await createResearchProject(empty, DRAFT, { delayMs: 0, now: NOW })

    // Fixture identifiers stay reserved, so fixture jobs are never attributed to the draft.
    expect(project.id).toBe('proj-003')
    for (const id of ['workspace', 'execution', 'results']) {
      expect(snapshot.pages.find((p) => p.id === id)?.status).toBe('locked')
    }
    const [progress] = deriveDashboard(snapshot).projects
    expect(progress.latestJob).toBeNull()
    expect(progress.next.kind).toBe('submit_request')
  })

  it('rejects an invalid draft without changing the snapshot', async () => {
    const snapshot = await load()
    await expect(
      createResearchProject(snapshot, { title: '', summary: '' }, { delayMs: 0, now: NOW }),
    ).rejects.toThrow('corrigez les champs signalés')
    expect(snapshot.projects).toHaveLength(2)
  })
})
