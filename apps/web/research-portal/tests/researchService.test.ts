import { describe, expect, it } from 'vitest'
import {
  DEMO_RESEARCHER_ID,
  derivePages,
  isAuthorized,
  loadResearchSnapshot,
  PAGE_DEFINITIONS,
  scenarioFromSearch,
} from '../src/services/researchService'
import type { PortalPage } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const load = (scenario?: 'nominal' | 'empty' | 'error') =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { scenario, delayMs: 0, now: NOW })

const byId = (pages: PortalPage[], id: string) => pages.find((p) => p.id === id)

describe('Research Portal service (MOCKED, canonical fixtures)', () => {
  it("loads Dr Rezgui's fictional projects with their Governance decision", async () => {
    const snapshot = await load()
    expect(snapshot.researcher.lastName).toBe('Rezgui')
    expect(snapshot.organization.id).toBe('org-research-lab')
    expect(snapshot.projects.map((s) => s.project.id)).toEqual(['proj-002', 'proj-001'])

    const [asthma, cardio] = snapshot.projects
    expect(cardio.request?.status).toBe('approved')
    expect(cardio.decision?.id).toBe('dec-rar-001')
    expect(cardio.participatingOrganizations.map((o) => o.id)).toEqual(['org-hospital-a', 'org-hospital-b'])
    expect(asthma.request?.status).toBe('under_review')
    expect(asthma.decision).toBeNull()
    expect(snapshot.notifications.map((n) => n.id)).toContain('notif-009')
  })

  it('derives one page per ticket, in workflow order', async () => {
    const { pages } = await load()
    expect(pages.map((p) => p.ticket)).toEqual(PAGE_DEFINITIONS.map((d) => d.ticket))
    expect(byId(pages, 'request-status')?.detail).toBe('1 approuvée(s), 1 en revue.')
    expect(byId(pages, 'sciagents')?.detail).toContain('MOCKED')
  })

  it('only authorizes Compute-to-Data under a valid Governance approval', async () => {
    const { projects } = await load()
    const cardio = projects.find((s) => s.project.id === 'proj-001')!
    const asthma = projects.find((s) => s.project.id === 'proj-002')!
    expect(isAuthorized(cardio, NOW)).toBe(true)
    expect(isAuthorized(asthma, NOW)).toBe(false)
    expect(isAuthorized(cardio, new Date('2027-08-01T00:00:00+01:00'))).toBe(false)

    const pendingOnly = derivePages([asthma], NOW)
    for (const id of ['workspace', 'execution', 'results']) {
      expect(byId(pendingOnly, id)?.status).toBe('locked')
    }
    expect(byId(derivePages([cardio], NOW), 'workspace')?.status).toBe('available')

    const later = await loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: new Date('2027-08-01T00:00:00+01:00') })
    expect(later.projects.find((s) => s.project.id === 'proj-001')?.authorized).toBe(false)
    expect(byId(later.pages, 'results')?.status).toBe('locked')
  })

  it('supports explicit empty and error demo scenarios', async () => {
    const empty = await load('empty')
    expect(empty.projects).toEqual([])
    expect(empty.jobs).toEqual([])
    expect(empty.notifications).toEqual([])
    expect(byId(empty.pages, 'execution')?.status).toBe('locked')
    expect(byId(empty.pages, 'new-project')?.status).toBe('available')

    await expect(load('error')).rejects.toThrow('indisponible')
  })

  it('refuses an identity that is not a researcher', async () => {
    await expect(loadResearchSnapshot('usr-olfa', { delayMs: 0 })).rejects.toThrow('inconnu')
  })

  it('reads the demo scenario from the URL', () => {
    expect(scenarioFromSearch('?demo=vide')).toBe('empty')
    expect(scenarioFromSearch('?demo=erreur')).toBe('error')
    expect(scenarioFromSearch('')).toBe('nominal')
  })
})
