import { describe, expect, it } from 'vitest'
import { deriveDashboard, type ProjectProgress } from '../src/services/dashboard'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot } from '../src/services/researchService'
import type { ComputeJob, ProjectSummary, ResearchSnapshot } from '../src/types/research'

const load = (now = '2026-10-10T12:00:00+01:00', scenario?: 'empty') =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { scenario, delayMs: 0, now: new Date(now) })

const states = (progress: ProjectProgress) => progress.steps.map((s) => s.state)
const byProject = (projects: ProjectProgress[], id: string) => projects.find((p) => p.summary.project.id === id)!

/** The approved cardiometabolic project, with its request, decision, or jobs replaced. */
async function cardioWith(
  change: (summary: ProjectSummary) => Partial<ProjectSummary>,
  jobs: (jobs: ComputeJob[]) => ComputeJob[] = (j) => j,
): Promise<ProjectProgress> {
  const snapshot = await load()
  const cardio = snapshot.projects.find((s) => s.project.id === 'proj-001')!
  const changed: ResearchSnapshot = {
    ...snapshot,
    projects: [{ ...cardio, ...change(cardio) }],
    jobs: jobs(snapshot.jobs),
  }
  return deriveDashboard(changed).projects[0]
}

describe('Researcher dashboard (HC-091, MOCKED fixtures)', () => {
  it('summarizes the fictional projects, executions, and results', async () => {
    const { metrics, jobs } = deriveDashboard(await load())
    expect(metrics).toEqual({
      projects: 2,
      requestsUnderReview: 1,
      validAuthorizations: 1,
      completedJobs: 1,
      jobs: 1,
      releasedResults: 1,
    })
    expect(jobs.map((j) => j.id)).toEqual(['job-001'])
  })

  it('places each project in the governed workflow with its next action', async () => {
    const { projects } = deriveDashboard(await load())
    // Ready actions come before actions waiting on someone else.
    expect(projects.map((p) => p.summary.project.id)).toEqual(['proj-001', 'proj-002'])

    const cardio = byProject(projects, 'proj-001')
    expect(states(cardio)).toEqual(['done', 'done', 'done', 'done', 'done'])
    expect(cardio.next).toEqual({ kind: 'review_result', priority: 'ready', page: 'results' })
    expect(cardio.result?.id).toBe('res-001')
    expect(cardio.steps.find((s) => s.id === 'execution')?.at).toBe('2026-09-12T10:05:30+01:00')

    const asthma = byProject(projects, 'proj-002')
    expect(states(asthma)).toEqual(['done', 'done', 'current', 'upcoming', 'upcoming'])
    expect(asthma.next).toEqual({ kind: 'await_decision', priority: 'waiting', page: 'request-status' })
  })

  it('exposes result release metadata only, never aggregate rows', async () => {
    const snapshot = await load()
    expect(snapshot.results).toHaveLength(1)
    expect(snapshot.results[0]).not.toHaveProperty('rows')
    expect(snapshot.results[0].disclosureCheck).toBe('passed')
  })

  it('flags an approval close to its end, then expired', async () => {
    const valid = deriveDashboard(await load()).authorizations
    expect(valid.map((a) => [a.summary.project.id, a.state])).toEqual([['proj-001', 'valid']])
    expect(valid[0].daysLeft).toBe(283)

    const [expiring] = deriveDashboard(await load('2027-07-01T12:00:00+01:00')).authorizations
    expect(expiring.state).toBe('expiring')
    expect(expiring.daysLeft).toBe(19)

    const later = deriveDashboard(await load('2027-08-01T12:00:00+01:00'))
    expect(later.authorizations[0].state).toBe('expired')
    expect(later.metrics.validAuthorizations).toBe(0)
    const cardio = byProject(later.projects, 'proj-001')
    expect(cardio.steps.find((s) => s.id === 'decision')).toMatchObject({ state: 'blocked', reason: 'expired' })
    expect(cardio.next).toEqual({ kind: 'renew_request', priority: 'attention', page: 'submit-request' })
    expect(later.projects[0]).toBe(cardio)
  })

  it('derives the earlier and failing states of the workflow', async () => {
    const notSubmitted = await cardioWith(() => ({ request: null, decision: null, authorized: false }), () => [])
    expect(states(notSubmitted)).toEqual(['done', 'current', 'upcoming', 'upcoming', 'upcoming'])
    expect(notSubmitted.next.kind).toBe('submit_request')

    const rejected = await cardioWith(
      ({ request, decision }) => ({
        request: { ...request!, status: 'rejected' },
        decision: { ...decision!, outcome: 'rejected' },
        authorized: false,
      }),
      () => [],
    )
    expect(rejected.steps.find((s) => s.id === 'decision')).toMatchObject({ state: 'blocked', reason: 'rejected' })
    expect(rejected.next).toMatchObject({ kind: 'request_rejected', priority: 'attention' })

    const noJob = await cardioWith(() => ({}), () => [])
    expect(states(noJob)).toEqual(['done', 'done', 'done', 'current', 'upcoming'])
    expect(noJob.next).toEqual({ kind: 'prepare_execution', priority: 'ready', page: 'workspace' })

    const running = await cardioWith(
      () => ({}),
      (jobs) => jobs.map((j) => ({ ...j, status: 'running', controlledResultId: null })),
    )
    expect(running.next).toMatchObject({ kind: 'follow_execution', page: 'execution' })

    const failed = await cardioWith(
      () => ({}),
      (jobs) => jobs.map((j) => ({ ...j, status: 'failed', controlledResultId: null })),
    )
    expect(failed.steps.find((s) => s.id === 'execution')).toMatchObject({ state: 'blocked', reason: 'failed' })
    expect(failed.next).toMatchObject({ kind: 'execution_failed', priority: 'attention' })
  })

  it('is empty when the researcher has no project', async () => {
    const dashboard = deriveDashboard(await load(undefined, 'empty'))
    expect(dashboard.projects).toEqual([])
    expect(dashboard.authorizations).toEqual([])
    expect(dashboard.metrics.projects).toBe(0)
  })
})
