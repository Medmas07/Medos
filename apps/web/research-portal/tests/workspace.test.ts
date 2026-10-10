import { describe, expect, it } from 'vitest'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot, type DemoScenario } from '../src/services/researchService'
import {
  addCell,
  checkCell,
  isStale,
  notebookFor,
  recordCellRun,
  removeCell,
  runCell,
  starterNotebook,
  updateCellSource,
  withNotebook,
  workspaceAccess,
} from '../src/services/workspace'
import type { ComputeJobStage, ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')
const FIXTURE_CODE_CELL = 'nb-001-cell-2'

const load = (now = NOW, scenario: DemoScenario = 'nominal') =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now, scenario })

async function fixtureContext() {
  const snapshot = await load()
  const context = workspaceAccess(snapshot).contexts[0]
  return { snapshot, context, notebook: notebookFor(snapshot, context) }
}

const states = (source: string, context: Awaited<ReturnType<typeof fixtureContext>>['context'], now = NOW) =>
  Object.fromEntries(checkCell(source, context, now).map((c) => [c.id, c.state]))

describe('Research workspace (HC-099, MOCKED)', () => {
  it('opens only for a project with a valid Governance approval, with its authorization context', async () => {
    const access = workspaceAccess(await load())
    expect(access.contexts.map((c) => c.summary.project.id)).toEqual(['proj-001'])
    expect(access.unavailable.map((u) => [u.summary.project.id, u.reason])).toEqual([['proj-002', 'under_review']])

    const [context] = access.contexts
    expect(context.decision.id).toBe('dec-rar-001')
    expect(context.authorization).toMatchObject({ state: 'valid' })
    expect(context.nodes.map((o) => o.node?.id)).toEqual(['node-hospital-a', 'node-hospital-b'])
    expect(context.variables.map((v) => v.name)).toEqual(['age_band', 'sex', 'hba1c', 'treated_hypertension'])
    expect(context.minimumCellSize).toBe(10)
  })

  it('closes once the approval has expired, and in the empty scenario', async () => {
    const expired = workspaceAccess(await load(new Date('2027-08-01T12:00:00+01:00')))
    expect(expired.contexts).toEqual([])
    expect(expired.unavailable.find((u) => u.summary.project.id === 'proj-001')?.reason).toBe('expired')

    const empty = await load(NOW, 'empty')
    expect(workspaceAccess(empty)).toEqual({ contexts: [], unavailable: [] })
    expect(empty.notebooks).toEqual([])
  })

  it('loads the fixture notebook, and a starter notebook for an authorized project without one', async () => {
    const { snapshot, context, notebook } = await fixtureContext()
    expect(notebook.id).toBe('nb-001')
    expect(notebook.cells.map((c) => c.type)).toEqual(['markdown', 'code'])

    const starter = notebookFor({ ...snapshot, notebooks: [] }, context)
    expect(starter).toEqual(starterNotebook(context))
    expect(starter.cells[1].source).toContain('min_cell_size=10')
    expect(Object.values(states(starter.cells[1].source, context))).not.toContain('failed')
  })

  it('passes the fixture code and refuses code outside the authorization', async () => {
    const { context, notebook } = await fixtureContext()
    expect(states(notebook.cells[1].source, context)).toEqual({
      authorization: 'passed',
      approved_packages: 'passed',
      no_system_access: 'passed',
      authorized_variables: 'passed',
      minimum_cell_size: 'passed',
      controlled_release: 'passed',
    })

    expect(states('import requests\nimport pandas as pd\nctd.release(1)', context).approved_packages).toBe('failed')
    expect(states('from os import path', context).approved_packages).toBe('failed')
    expect(states('data = open("export.csv")', context).no_system_access).toBe('failed')
    expect(states('cohort.group_by("asthma")', context).authorized_variables).toBe('failed')
    expect(states('ctd.release(result, min_cell_size=5)', context).minimum_cell_size).toBe('failed')
    expect(states('x = ctd.cohort()', context).controlled_release).toBe('warning')
    expect(states('   ', context)).toEqual({ authorization: 'passed', not_empty: 'failed' })
    expect(states(notebook.cells[1].source, context, new Date('2027-08-01T12:00:00+01:00')).authorization).toBe('failed')
  })

  it('simulates every stage and returns the fixture result for the unchanged fixture cell', async () => {
    const { context, notebook } = await fixtureContext()
    const progress: ComputeJobStage[][] = []
    const run = await runCell(notebook, FIXTURE_CODE_CELL, context, {
      now: NOW,
      stageDelayMs: 0,
      onProgress: (stages) => progress.push(stages),
    })

    expect(run).toMatchObject({ number: 1, status: 'completed', source: notebook.cells[1].source })
    expect(run.algorithmSha256).toMatch(/^[a-f0-9]{64}$/)
    expect(run.stages.map((s) => [s.stage, s.organizationId, s.status])).toEqual([
      ['authorization_check', 'org-governance', 'completed'],
      ['execution', 'org-hospital-a', 'completed'],
      ['execution', 'org-hospital-b', 'completed'],
      ['aggregation', 'org-platform', 'completed'],
      ['output_validation', 'org-platform', 'completed'],
    ])
    expect(progress.some((stages) => stages.some((s) => s.status === 'running'))).toBe(true)
    expect(run.output).toMatchObject({ kind: 'aggregate', result: { id: 'res-001', disclosureCheck: 'passed' } })
    if (run.output.kind === 'aggregate') expect(run.output.rows).toHaveLength(4)
  })

  it('computes nothing for edited code, and returns nothing without ctd.release', async () => {
    const { context, notebook } = await fixtureContext()
    const edited = updateCellSource(notebook, FIXTURE_CODE_CELL, notebook.cells[1].source.replace('age_max=79', 'age_max=69'))
    expect((await runCell(edited, FIXTURE_CODE_CELL, context, { now: NOW, stageDelayMs: 0 })).output).toEqual({
      kind: 'not_simulated',
    })

    const silent = updateCellSource(notebook, FIXTURE_CODE_CELL, 'cohort = ctd.cohort(age_min=40)')
    const run = await runCell(silent, FIXTURE_CODE_CELL, context, { now: NOW, stageDelayMs: 0 })
    expect(run).toMatchObject({ status: 'completed', output: { kind: 'no_release' } })
  })

  it('refuses a failing cell before any stage, and refuses once the approval has expired', async () => {
    const { context, notebook } = await fixtureContext()
    const bad = updateCellSource(notebook, FIXTURE_CODE_CELL, 'import socket\nctd.release(r, min_cell_size=3)')
    const refused = await runCell(bad, FIXTURE_CODE_CELL, context, { now: NOW, stageDelayMs: 0 })
    expect(refused).toMatchObject({ status: 'refused', stages: [], output: { kind: 'none' } })
    expect(refused.error).toContain('socket')

    const late = await runCell(notebook, FIXTURE_CODE_CELL, context, {
      now: new Date('2027-08-01T12:00:00+01:00'),
      stageDelayMs: 0,
    })
    expect(late.status).toBe('refused')
  })

  it('fails without releasing anything when a Hospital Node execution fails', async () => {
    const { context, notebook } = await fixtureContext()
    let asked = 0
    const run = await runCell(notebook, FIXTURE_CODE_CELL, context, {
      now: NOW,
      stageDelayMs: 0,
      failLastNode: () => (asked++, true),
    })
    expect(asked).toBe(1)
    expect(run).toMatchObject({ status: 'failed', output: { kind: 'none' } })
    expect(run.stages.map((s) => s.status)).toEqual(['completed', 'completed', 'failed', 'pending', 'pending'])
    expect(run.error).toContain('node-hospital-b')

    const degraded = {
      ...context,
      nodes: [...context.nodes, { ...context.nodes[0], id: 'org-private-practice', shortName: 'Cabinet Bouzid', node: { id: 'node-private-practice', status: 'degraded' as const, dmiState: 'disconnected' as const } }],
    }
    expect((await runCell(notebook, FIXTURE_CODE_CELL, degraded, { now: NOW, stageDelayMs: 0 })).status).toBe('failed')
  })

  it('does not ask for the failure scenario when a cell is refused', async () => {
    const { context, notebook } = await fixtureContext()
    let asked = 0
    const empty = updateCellSource(notebook, FIXTURE_CODE_CELL, '')
    await runCell(empty, FIXTURE_CODE_CELL, context, { now: NOW, stageDelayMs: 0, failLastNode: () => (asked++, true) })
    expect(asked).toBe(0)
  })

  it('stops when interrupted', async () => {
    const { context, notebook } = await fixtureContext()
    const controller = new AbortController()
    const pending = runCell(notebook, FIXTURE_CODE_CELL, context, { now: NOW, stageDelayMs: 50, signal: controller.signal })
    controller.abort()
    await expect(pending).rejects.toThrow('interrompue')
  })

  it('edits the notebook in session state and flags stale output', async () => {
    const { snapshot, context, notebook } = await fixtureContext()
    const run = await runCell(notebook, FIXTURE_CODE_CELL, context, { now: NOW, stageDelayMs: 0 })
    let next = recordCellRun(notebook, FIXTURE_CODE_CELL, run)
    expect(isStale(next.cells[1])).toBe(false)
    next = updateCellSource(next, FIXTURE_CODE_CELL, next.cells[1].source + '\n')
    expect(isStale(next.cells[1])).toBe(true)
    expect((await runCell(next, FIXTURE_CODE_CELL, context, { now: NOW, stageDelayMs: 0 })).number).toBe(2)

    next = addCell(addCell(next, 'code'), 'markdown')
    expect(next.cells.map((c) => c.id)).toEqual(['nb-001-cell-1', 'nb-001-cell-2', 'nb-001-cell-3', 'nb-001-cell-4'])
    next = removeCell(next, 'nb-001-cell-3')
    expect(addCell(next, 'code').cells.at(-1)?.id).toBe('nb-001-cell-5')

    const updated: ResearchSnapshot = withNotebook(snapshot, next)
    expect(updated.notebooks).toHaveLength(1)
    expect(notebookFor(updated, context).cells).toHaveLength(3)
    expect(withNotebook(snapshot, starterNotebook(context)).notebooks.map((n) => n.id)).toEqual(['nb-001', 'nb-proj-001'])
  })
})
