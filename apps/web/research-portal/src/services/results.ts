import type { ControlledResultSummary, Organization, ProjectSummary, ResearchSnapshot } from '../types/research'
import { listExecutions, type Execution } from './executions'
import { organizationsByIds } from './researchService'

/**
 * Research experiment result panel (HC-101), MOCKED. It joins each released
 * controlled result of the fixtures (HC-005) to the executions that released
 * it (HC-100), the Governance decision they are bound to, and the Hospital
 * Nodes whose local aggregates were combined. A result is a research
 * aggregate: it never becomes clinical data, and nothing here recomputes it.
 */

export interface ResultTable {
  columns: string[]
  rows: (string | number)[][]
}

export interface ControlledResultEntry {
  result: ControlledResultSummary
  summary: ProjectSummary
  /**
   * The executions that released it, most recent first: its fixture job and
   * any workspace run of the unchanged fixture cell, which returns the same
   * fixture result without recomputing it.
   */
  releases: Execution[]
  /** The execution that produced it, `result.jobId`; null if it is not among the researcher's executions. */
  source: Execution | null
  /** Organizations whose Hospital Node ran the analysis and whose aggregates were combined. */
  sourceOrganizations: Organization[]
  /** The aggregate table; null when the disclosure check failed, as nothing is then released. */
  table: ResultTable | null
}

/** Why an execution released no controlled result. */
export type WithheldReason = 'in_progress' | 'failed' | 'no_release' | 'not_simulated'

export interface WithheldExecution {
  execution: Execution
  reason: WithheldReason
}

export interface ResultsOverview {
  results: ControlledResultEntry[]
  withheld: WithheldExecution[]
}

function withheldReason(execution: Execution): WithheldReason {
  if (execution.status === 'failed') return 'failed'
  if (execution.status !== 'completed') return 'in_progress'
  return execution.output === 'no_release' ? 'no_release' : 'not_simulated'
}

/**
 * The researcher's controlled results, most recently released first, and the
 * executions that released none. `tableOf` returns a released result's
 * aggregate table. Pure.
 */
export function resultsOverview(
  snapshot: ResearchSnapshot,
  tableOf: (resultId: string) => ResultTable | null,
): ResultsOverview {
  const executions = listExecutions(snapshot)
  const results: ControlledResultEntry[] = []

  for (const result of snapshot.results) {
    const releases = executions.filter((e) => e.resultId === result.id)
    const source = executions.find((e) => e.id === result.jobId) ?? null
    const summary = (source ?? releases[0])?.summary
    if (!summary) continue
    const nodeStages = (source ?? releases[0]).stages.filter((s) => s.stage === 'execution' && s.status === 'completed')
    results.push({
      result,
      summary,
      releases,
      source,
      sourceOrganizations: organizationsByIds(nodeStages.map((s) => s.organizationId)),
      table: result.disclosureCheck === 'passed' ? tableOf(result.id) : null,
    })
  }

  const lastRelease = (entry: ControlledResultEntry) => new Date(entry.releases[0]?.submittedAt ?? 0).getTime()
  results.sort((a, b) => lastRelease(b) - lastRelease(a))

  return {
    results,
    withheld: executions.filter((e) => e.resultId === null).map((execution) => ({ execution, reason: withheldReason(execution) })),
  }
}

/** The stage end time of the source execution: when its aggregate was combined, and when it was checked. Pure. */
export function resultTimes(entry: ControlledResultEntry): { aggregatedAt: string | null; checkedAt: string | null } {
  const at = (stage: string) => entry.source?.stages.find((s) => s.stage === stage)?.completedAt ?? null
  return { aggregatedAt: at('aggregation'), checkedAt: at('output_validation') }
}
