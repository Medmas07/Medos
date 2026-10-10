import type {
  ComputeJob,
  ControlledResultSummary,
  PageId,
  ProjectSummary,
  ResearchSnapshot,
} from '../types/research'

/**
 * Researcher dashboard (HC-091): pure derivations over the MOCKED research
 * snapshot. Nothing here decides an access request or runs a job; it only
 * reads the Governance decisions and simulated executions already loaded.
 */

/** An approval ending within this many days is flagged on the dashboard. */
export const EXPIRY_WARNING_DAYS = 30

const DAY_MS = 24 * 60 * 60 * 1000

/** Steps of the governed research workflow, from project to controlled result. */
export type LifecycleStepId = 'project' | 'request' | 'decision' | 'execution' | 'result'

export type StepState = 'done' | 'current' | 'blocked' | 'upcoming'

export interface LifecycleStep {
  id: LifecycleStepId
  state: StepState
  /** When the step was reached (ISO 8601), if it was. */
  at: string | null
  /** Why a step is blocked. */
  reason?: 'rejected' | 'expired' | 'failed' | 'disclosure_failed'
}

export type NextActionKind =
  | 'submit_request'
  | 'await_decision'
  | 'request_rejected'
  | 'renew_request'
  | 'prepare_execution'
  | 'follow_execution'
  | 'execution_failed'
  | 'await_result'
  | 'review_result'

/** `attention`: the researcher must act on a problem; `ready`: a step can be taken; `waiting`: someone else acts. */
export type ActionPriority = 'attention' | 'ready' | 'waiting'

export interface NextAction {
  kind: NextActionKind
  priority: ActionPriority
  page: PageId
}

export interface ProjectProgress {
  summary: ProjectSummary
  steps: LifecycleStep[]
  next: NextAction
  latestJob: ComputeJob | null
  result: ControlledResultSummary | null
}

export type AuthorizationState = 'valid' | 'expiring' | 'expired'

export interface AuthorizationStatus {
  summary: ProjectSummary
  state: AuthorizationState
  /** Whole days until the approval ends; null when it has no end date. Negative once expired. */
  daysLeft: number | null
}

export interface DashboardMetrics {
  projects: number
  requestsUnderReview: number
  validAuthorizations: number
  completedJobs: number
  jobs: number
  releasedResults: number
}

export interface ResearchDashboard {
  metrics: DashboardMetrics
  /** Projects ordered by priority of their next action, then most recent first. */
  projects: ProjectProgress[]
  authorizations: AuthorizationStatus[]
  /** The researcher's executions, most recent first. */
  jobs: ComputeJob[]
}

const PRIORITY_ORDER: Record<ActionPriority, number> = { attention: 0, ready: 1, waiting: 2 }

function latestJobOf(projectId: string, jobs: ComputeJob[]): ComputeJob | null {
  return (
    jobs
      .filter((j) => j.projectId === projectId)
      .sort((a, b) => b.submittedAt.localeCompare(a.submittedAt))[0] ?? null
  )
}

function isExpired(summary: ProjectSummary): boolean {
  return summary.request?.status === 'approved' && summary.decision?.outcome === 'approved' && !summary.authorized
}

function deriveSteps(
  summary: ProjectSummary,
  job: ComputeJob | null,
  result: ControlledResultSummary | null,
): LifecycleStep[] {
  const { project, request, decision, authorized } = summary

  const requestStep: LifecycleStep = request
    ? { id: 'request', state: 'done', at: request.submittedAt }
    : { id: 'request', state: 'current', at: null }

  let decisionStep: LifecycleStep
  if (!request) decisionStep = { id: 'decision', state: 'upcoming', at: null }
  else if (request.status === 'under_review' || !decision) decisionStep = { id: 'decision', state: 'current', at: null }
  else if (request.status === 'rejected' || decision.outcome === 'rejected')
    decisionStep = { id: 'decision', state: 'blocked', at: decision.decidedAt, reason: 'rejected' }
  else if (!authorized) decisionStep = { id: 'decision', state: 'blocked', at: decision.decidedAt, reason: 'expired' }
  else decisionStep = { id: 'decision', state: 'done', at: decision.decidedAt }

  let executionStep: LifecycleStep
  if (job?.status === 'completed') {
    const finished = job.stages.map((s) => s.completedAt ?? '').sort().at(-1) || null
    executionStep = { id: 'execution', state: 'done', at: finished }
  } else if (job?.status === 'failed') executionStep = { id: 'execution', state: 'blocked', at: job.submittedAt, reason: 'failed' }
  else if (job) executionStep = { id: 'execution', state: 'current', at: job.submittedAt }
  else executionStep = { id: 'execution', state: authorized ? 'current' : 'upcoming', at: null }

  let resultStep: LifecycleStep
  if (result?.disclosureCheck === 'passed') resultStep = { id: 'result', state: 'done', at: executionStep.at }
  else if (result) resultStep = { id: 'result', state: 'blocked', at: null, reason: 'disclosure_failed' }
  else resultStep = { id: 'result', state: job?.status === 'completed' ? 'current' : 'upcoming', at: null }

  return [{ id: 'project', state: 'done', at: project.createdAt }, requestStep, decisionStep, executionStep, resultStep]
}

function deriveNextAction(summary: ProjectSummary, job: ComputeJob | null, result: ControlledResultSummary | null): NextAction {
  const { request, decision, authorized } = summary
  if (!request) return { kind: 'submit_request', priority: 'ready', page: 'submit-request' }
  if (request.status === 'rejected' || decision?.outcome === 'rejected')
    return { kind: 'request_rejected', priority: 'attention', page: 'request-status' }
  if (isExpired(summary)) return { kind: 'renew_request', priority: 'attention', page: 'submit-request' }
  if (!authorized) return { kind: 'await_decision', priority: 'waiting', page: 'request-status' }
  if (!job) return { kind: 'prepare_execution', priority: 'ready', page: 'workspace' }
  if (job.status === 'failed') return { kind: 'execution_failed', priority: 'attention', page: 'execution' }
  if (job.status !== 'completed') return { kind: 'follow_execution', priority: 'waiting', page: 'execution' }
  if (!result) return { kind: 'await_result', priority: 'waiting', page: 'results' }
  return { kind: 'review_result', priority: 'ready', page: 'results' }
}

/** A Governance approval's validity at `now`; null when the request is not approved. Pure. */
export function authorizationStatus(summary: ProjectSummary, now: Date): AuthorizationStatus | null {
  const { request, decision } = summary
  if (request?.status !== 'approved' || decision?.outcome !== 'approved') return null
  if (decision.validUntil === null) return { summary, state: 'valid', daysLeft: null }
  const daysLeft = Math.floor((new Date(decision.validUntil).getTime() - now.getTime()) / DAY_MS)
  const state: AuthorizationState = !summary.authorized
    ? 'expired'
    : daysLeft < EXPIRY_WARNING_DAYS
      ? 'expiring'
      : 'valid'
  return { summary, state, daysLeft }
}

/** Derives the researcher dashboard from a loaded snapshot, at the snapshot's reference time. Pure. */
export function deriveDashboard(snapshot: ResearchSnapshot): ResearchDashboard {
  const now = new Date(snapshot.asOf)

  const projects = snapshot.projects
    .map((summary) => {
      const latestJob = latestJobOf(summary.project.id, snapshot.jobs)
      const result = snapshot.results.find((r) => r.id === latestJob?.controlledResultId) ?? null
      return {
        summary,
        steps: deriveSteps(summary, latestJob, result),
        next: deriveNextAction(summary, latestJob, result),
        latestJob,
        result,
      }
    })
    .sort(
      (a, b) =>
        PRIORITY_ORDER[a.next.priority] - PRIORITY_ORDER[b.next.priority] ||
        b.summary.project.createdAt.localeCompare(a.summary.project.createdAt),
    )

  const authorizations = snapshot.projects
    .map((s) => authorizationStatus(s, now))
    .filter((a): a is AuthorizationStatus => a !== null)

  return {
    metrics: {
      projects: snapshot.projects.length,
      requestsUnderReview: snapshot.projects.filter((s) => s.request?.status === 'under_review').length,
      validAuthorizations: snapshot.projects.filter((s) => s.authorized).length,
      completedJobs: snapshot.jobs.filter((j) => j.status === 'completed').length,
      jobs: snapshot.jobs.length,
      releasedResults: snapshot.results.filter((r) => r.disclosureCheck === 'passed').length,
    },
    projects,
    authorizations,
    jobs: [...snapshot.jobs].sort((a, b) => b.submittedAt.localeCompare(a.submittedAt)),
  }
}
