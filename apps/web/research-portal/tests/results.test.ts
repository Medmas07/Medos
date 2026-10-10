import { describe, expect, it } from 'vitest'
import { controlledResultTable, DEMO_RESEARCHER_ID, loadResearchSnapshot, type DemoScenario } from '../src/services/researchService'
import { resultsOverview, resultTimes } from '../src/services/results'
import { notebookFor, recordCellRun, runCell, updateCellSource, withNotebook, workspaceAccess } from '../src/services/workspace'
import type { ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const load = (scenario: DemoScenario = 'nominal') =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: NOW, scenario })

const overview = (snapshot: ResearchSnapshot) => resultsOverview(snapshot, controlledResultTable)

/** The snapshot after running the fixture code cell, with every stage simulated instantly. */
async function afterRun(edit?: string, failLastNode = false) {
  const snapshot = await load()
  const context = workspaceAccess(snapshot).contexts[0]
  let notebook = notebookFor(snapshot, context)
  if (edit !== undefined) notebook = updateCellSource(notebook, 'nb-001-cell-2', edit)
  const run = await runCell(notebook, 'nb-001-cell-2', context, { now: NOW, stageDelayMs: 0, failLastNode: () => failLastNode })
  return withNotebook(snapshot, recordCellRun(notebook, 'nb-001-cell-2', run))
}

describe('Research experiment result panel (HC-101, MOCKED)', () => {
  it('shows the fixture result with its aggregate table, source job, and Hospital Nodes', async () => {
    const { results, withheld } = overview(await load())
    expect(results).toHaveLength(1)
    const [entry] = results
    expect(entry.result).toMatchObject({ id: 'res-001', jobId: 'job-001', minimumCellSize: 10, disclosureCheck: 'passed' })
    expect(entry.summary.project.id).toBe('proj-001')
    expect(entry.source?.decisionId).toBe('dec-rar-001')
    expect(entry.releases.map((e) => e.id)).toEqual(['job-001'])
    expect(entry.sourceOrganizations.map((o) => o.id)).toEqual(['org-hospital-a', 'org-hospital-b'])
    expect(entry.table?.columns).toEqual(["Tranche d'âge", 'Participants', 'HbA1c > 7 % (%)'])
    expect(entry.table?.rows).toHaveLength(4)
    expect(resultTimes(entry)).toEqual({ aggregatedAt: '2026-09-12T10:05:00+01:00', checkedAt: '2026-09-12T10:05:30+01:00' })
    expect(withheld).toEqual([])
  })

  it('every released cell count reaches the minimum cell size', async () => {
    const [entry] = overview(await load()).results
    for (const row of entry.table!.rows) expect(row[1]).toBeGreaterThanOrEqual(entry.result.minimumCellSize)
  })

  it('shows nothing in the empty scenario', async () => {
    expect(overview(await load('empty'))).toEqual({ results: [], withheld: [] })
  })

  it('withholds the table of a result that failed its disclosure check', async () => {
    const snapshot = await load()
    const failed = { ...snapshot, results: snapshot.results.map((r) => ({ ...r, disclosureCheck: 'failed' as const })) }
    const [entry] = overview(failed).results
    expect(entry.table).toBeNull()
    expect(controlledResultTable('res-unknown')).toBeNull()
  })

  it('lists a workspace run of the unchanged fixture cell as a release of the same, not recomputed, result', async () => {
    const { results, withheld } = overview(await afterRun())
    expect(results).toHaveLength(1)
    expect(results[0].releases.map((e) => [e.id, e.origin])).toEqual([
      ['nb-001-cell-2-run-1', 'session'],
      ['job-001', 'fixture'],
    ])
    expect(results[0].source?.id).toBe('job-001')
    expect(withheld).toEqual([])
  })

  it('lists edited code, a run without ctd.release, and a failed run as releasing nothing', async () => {
    const edited = overview(
      await afterRun('result = ctd.cohort().group_by("sex").agg(n="count")\nctd.release(result, min_cell_size=10)'),
    )
    expect(edited.withheld.map((w) => [w.execution.id, w.reason])).toEqual([['nb-001-cell-2-run-1', 'not_simulated']])
    expect(edited.results[0].releases.map((e) => e.id)).toEqual(['job-001'])

    const noRelease = overview(await afterRun('result = ctd.cohort().group_by("sex").agg(n="count")'))
    expect(noRelease.withheld.map((w) => w.reason)).toEqual(['no_release'])

    const failed = overview(await afterRun(undefined, true))
    expect(failed.withheld.map((w) => w.reason)).toEqual(['failed'])
    expect(failed.withheld[0].execution.error).toBeTruthy()
  })

  it('keeps the results page locked without a still-valid Governance approval', async () => {
    const snapshot = await loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: new Date('2030-01-01T00:00:00Z') })
    expect(snapshot.pages.find((p) => p.id === 'results')?.status).toBe('locked')
  })
})
