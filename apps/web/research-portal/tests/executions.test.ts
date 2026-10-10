import { describe, expect, it } from 'vitest'
import { executionPhases, listExecutions, replayFrames, statusOfStages } from '../src/services/executions'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot, type DemoScenario } from '../src/services/researchService'
import { notebookFor, recordCellRun, runCell, updateCellSource, withNotebook, workspaceAccess } from '../src/services/workspace'
import type { ComputeJobStage } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const load = (scenario: DemoScenario = 'nominal') =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: NOW, scenario })

const phaseStates = (submittedAt: string, stages: ComputeJobStage[]) =>
  executionPhases(submittedAt, stages).map((p) => [p.id, p.state])

/** The snapshot after running a workspace cell, with every stage simulated instantly. */
async function afterRun(edit?: string, failLastNode = false) {
  const snapshot = await load()
  const context = workspaceAccess(snapshot).contexts[0]
  let notebook = notebookFor(snapshot, context)
  if (edit !== undefined) notebook = updateCellSource(notebook, 'nb-001-cell-2', edit)
  const run = await runCell(notebook, 'nb-001-cell-2', context, { now: NOW, stageDelayMs: 0, failLastNode: () => failLastNode })
  return withNotebook(snapshot, recordCellRun(notebook, 'nb-001-cell-2', run))
}

describe('Compute-to-Data execution visualization (HC-100, MOCKED)', () => {
  it('lists the fixture job with its five completed phases and released result', async () => {
    const [job] = listExecutions(await load())
    expect(job).toMatchObject({
      id: 'job-001',
      origin: 'fixture',
      decisionId: 'dec-rar-001',
      notebookId: 'nb-001',
      status: 'completed',
      resultId: 'res-001',
      finishedAt: '2026-09-12T10:05:30+01:00',
    })
    expect(job.summary.project.id).toBe('proj-001')
    expect(executionPhases(job.submittedAt, job.stages)).toEqual([
      { id: 'submitted', state: 'completed', at: '2026-09-12T10:00:00+01:00' },
      { id: 'authorization', state: 'completed', at: '2026-09-12T10:00:20+01:00' },
      { id: 'execution', state: 'completed', at: '2026-09-12T10:04:45+01:00' },
      { id: 'aggregation', state: 'completed', at: '2026-09-12T10:05:00+01:00' },
      { id: 'completed', state: 'completed', at: '2026-09-12T10:05:30+01:00' },
    ])
  })

  it('lists nothing in the empty scenario', async () => {
    expect(listExecutions(await load('empty'))).toEqual([])
  })

  it('adds the latest workspace run of a cell, most recent first', async () => {
    const executions = listExecutions(await afterRun())
    expect(executions.map((e) => e.id)).toEqual(['nb-001-cell-2-run-1', 'job-001'])
    expect(executions[0]).toMatchObject({
      origin: 'session',
      decisionId: 'dec-rar-001',
      cellId: 'nb-001-cell-2',
      runNumber: 1,
      status: 'completed',
      resultId: 'res-001',
      output: 'aggregate',
    })
    expect(executions[0].algorithmSha256).toMatch(/^[a-f0-9]{64}$/)
  })

  it('shows edited code completing without a computed result', async () => {
    const [run] = listExecutions(
      await afterRun('result = ctd.cohort().group_by("sex").agg(n="count")\nctd.release(result, min_cell_size=10)'),
    )
    expect(run).toMatchObject({ status: 'completed', resultId: null, output: 'not_simulated' })
  })

  it('leaves out a refused cell, which was never sent', async () => {
    const executions = listExecutions(await afterRun('import requests'))
    expect(executions.map((e) => e.id)).toEqual(['job-001'])
  })

  it('stops at the Hospital Node phase when a node fails, releasing nothing', async () => {
    const [run] = listExecutions(await afterRun(undefined, true))
    expect(run).toMatchObject({ status: 'failed', resultId: null })
    expect(run.error).toContain('node-hospital-b')
    expect(phaseStates(run.submittedAt, run.stages)).toEqual([
      ['submitted', 'completed'],
      ['authorization', 'completed'],
      ['execution', 'failed'],
      ['aggregation', 'pending'],
      ['completed', 'pending'],
    ])
  })

  it('replays Submitted, Authorized, Hospital A and B running in parallel, Aggregating, Completed', async () => {
    const [job] = listExecutions(await load())
    const frames = replayFrames(job.stages)
    const status = (frame: ComputeJobStage[]) => Object.fromEntries(frame.map((s) => [s.id, s.status]))

    expect(frames[0].every((s) => s.status === 'pending' && s.completedAt === undefined)).toBe(true)
    expect(statusOfStages(frames[0])).toBe('queued')
    expect(status(frames[1])['job-001-auth']).toBe('running')
    expect(status(frames[3])).toMatchObject({ 'job-001-exec-a': 'running', 'job-001-exec-b': 'running' })
    expect(phaseStates(job.submittedAt, frames[3])[2]).toEqual(['execution', 'running'])
    expect(status(frames[4])).toMatchObject({ 'job-001-exec-a': 'completed', 'job-001-exec-b': 'running' })
    expect(phaseStates(job.submittedAt, frames[6])[3]).toEqual(['aggregation', 'running'])
    expect(frames.at(-1)).toEqual(job.stages)
    expect(statusOfStages(frames.at(-1)!)).toBe('completed')
  })

  it('replays a failed run up to its failing node and ends on the recorded stages', async () => {
    const [run] = listExecutions(await afterRun(undefined, true))
    const frames = replayFrames(run.stages)
    expect(frames.at(-1)).toEqual(run.stages)
    expect(statusOfStages(frames.at(-1)!)).toBe('failed')
    expect(frames.some((f) => f.some((s) => s.stage === 'aggregation' && s.status !== 'pending'))).toBe(false)
  })
})
