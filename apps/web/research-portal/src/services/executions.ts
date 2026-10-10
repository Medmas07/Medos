import type { CellOutput, ComputeJob, ComputeJobStage, ProjectSummary, ResearchSnapshot } from '../types/research'

/**
 * Compute-to-Data execution visualization (HC-100), MOCKED. It reads the
 * fixture jobs (HC-005) and the simulated workspace runs kept in session state
 * (HC-099), and derives the governed path of each one: submitted, authorized
 * by the Governance Node, run locally in each Hospital Node, aggregated, then
 * completed after the disclosure check. A replay animates a recorded
 * execution; it runs nothing and contacts no Research Service, Governance
 * Node, or Hospital Node.
 */

export type ExecutionPhaseId = 'submitted' | 'authorization' | 'execution' | 'aggregation' | 'completed'

export interface ExecutionPhase {
  id: ExecutionPhaseId
  state: ComputeJobStage['status']
  /** When the phase ended (or, for `submitted`, when the execution was submitted). */
  at: string | null
}

export interface Execution {
  /** `job-001` for a fixture job, `<cell>-run-<n>` for a workspace run. */
  id: string
  origin: 'fixture' | 'session'
  summary: ProjectSummary
  /** The Governance decision the execution is bound to. */
  decisionId: string | null
  notebookId: string | null
  /** Workspace runs only: the code cell and its run number. */
  cellId: string | null
  runNumber: number | null
  submittedAt: string
  finishedAt: string | null
  status: ComputeJob['status']
  stages: ComputeJobStage[]
  /** The released controlled result, if any. */
  resultId: string | null
  /** Workspace runs only: what came back. */
  output: CellOutput['kind'] | null
  /** SHA-256 of the code sent, `algorithm.sha256` of the HC-182 job contract; unknown for fixture jobs. */
  algorithmSha256: string | null
  error: string | null
}

const STAGE_PHASES: [ComputeJobStage['stage'], ExecutionPhaseId][] = [
  ['authorization_check', 'authorization'],
  ['execution', 'execution'],
  ['aggregation', 'aggregation'],
  ['output_validation', 'completed'],
]

const latest = (dates: (string | undefined)[]): string | null =>
  dates.filter((d): d is string => d !== undefined).sort().at(-1) ?? null

/** One phase's state from its stages: failed if one failed, completed once all completed. Pure. */
function phaseOf(stages: ComputeJobStage[]): Pick<ExecutionPhase, 'state' | 'at'> {
  if (stages.length === 0) return { state: 'pending', at: null }
  const failed = stages.find((s) => s.status === 'failed')
  if (failed) return { state: 'failed', at: failed.completedAt ?? null }
  if (stages.every((s) => s.status === 'completed')) return { state: 'completed', at: latest(stages.map((s) => s.completedAt)) }
  if (stages.some((s) => s.status !== 'pending')) return { state: 'running', at: null }
  return { state: 'pending', at: null }
}

/** The five phases of an execution: Submitted → Authorized → Hospital Nodes running → Aggregating → Completed. Pure. */
export function executionPhases(submittedAt: string, stages: ComputeJobStage[]): ExecutionPhase[] {
  return [
    { id: 'submitted', state: 'completed', at: submittedAt },
    ...STAGE_PHASES.map(([stage, id]) => ({ id, ...phaseOf(stages.filter((s) => s.stage === stage)) })),
  ]
}

/** The overall status the stages show. Pure. */
export function statusOfStages(stages: ComputeJobStage[]): ComputeJob['status'] {
  if (stages.some((s) => s.status === 'failed')) return 'failed'
  if (stages.length > 0 && stages.every((s) => s.status === 'completed')) return 'completed'
  if (stages.some((s) => s.status !== 'pending')) return 'running'
  return 'queued'
}

/** The researcher's executions, fixture jobs and latest workspace run of each cell, most recent first. Pure. */
export function listExecutions(snapshot: ResearchSnapshot): Execution[] {
  const summaryOf = (projectId: string) => snapshot.projects.find((s) => s.project.id === projectId)
  const executions: Execution[] = []

  for (const job of snapshot.jobs) {
    const summary = summaryOf(job.projectId)
    if (!summary) continue
    executions.push({
      id: job.id,
      origin: 'fixture',
      summary,
      decisionId: job.authorizationDecisionId,
      notebookId: job.notebookId ?? null,
      cellId: null,
      runNumber: null,
      submittedAt: job.submittedAt,
      finishedAt: job.status === 'completed' || job.status === 'failed' ? latest(job.stages.map((s) => s.completedAt)) : null,
      status: job.status,
      stages: job.stages,
      resultId: job.controlledResultId,
      output: null,
      algorithmSha256: null,
      error: null,
    })
  }

  for (const notebook of snapshot.notebooks) {
    const summary = summaryOf(notebook.projectId)
    if (!summary) continue
    for (const cell of notebook.cells) {
      const run = cell.lastRun
      // A refused cell was never sent: it is not an execution.
      if (!run || run.status === 'refused') continue
      executions.push({
        id: `${cell.id}-run-${run.number}`,
        origin: 'session',
        summary,
        decisionId: summary.decision?.id ?? null,
        notebookId: notebook.id,
        cellId: cell.id,
        runNumber: run.number,
        submittedAt: run.startedAt,
        finishedAt: run.finishedAt,
        status: run.status,
        stages: run.stages,
        resultId: run.output.kind === 'aggregate' ? run.output.result.id : null,
        output: run.output.kind,
        algorithmSha256: run.algorithmSha256,
        error: run.error ?? null,
      })
    }
  }

  return executions.sort((a, b) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime())
}

/**
 * The frames of a replay of these recorded stages, ending on them. Every
 * stage starts pending; each phase then runs, the Hospital Nodes in parallel,
 * and its stages end in the order they ended, until the phase where the
 * execution stopped. Pure.
 */
export function replayFrames(recorded: ComputeJobStage[]): ComputeJobStage[][] {
  let current: ComputeJobStage[] = recorded.map((s) => ({ ...s, status: 'pending', completedAt: undefined }))
  const frames = [current]
  const change = (ids: string[], next: (s: ComputeJobStage) => ComputeJobStage) => {
    current = current.map((s) => (ids.includes(s.id) ? next(s) : s))
    frames.push(current)
  }

  for (const [stage] of STAGE_PHASES) {
    const reached = recorded.filter((s) => s.stage === stage && s.status !== 'pending')
    if (reached.length === 0) break
    change(
      reached.map((s) => s.id),
      (s) => ({ ...s, status: 'running' }),
    )
    const ended = reached
      .filter((s) => s.status !== 'running')
      .sort((a, b) => (a.completedAt ?? '').localeCompare(b.completedAt ?? ''))
    for (const s of ended) change([s.id], () => s)
    const all = recorded.filter((s) => s.stage === stage)
    if (ended.length < all.length || ended.some((s) => s.status === 'failed')) break
  }
  return frames
}
