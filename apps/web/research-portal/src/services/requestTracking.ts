import type {
  GovernanceDecision,
  ProjectSummary,
  ResearchAccessRequest,
  ResearchSnapshot,
  StaffMember,
} from '../types/research'
import { authorizationStatus, type AuthorizationStatus, type StepState } from './dashboard'
import { FIXTURE_ACCESS_REQUESTS, staffMemberById } from './researchService'

/**
 * Research request tracking (HC-098): pure derivations over the MOCKED research
 * snapshot. The portal only reads the Governance decisions already loaded; it
 * cannot record, change, or anticipate one. A request submitted in this session
 * (HC-097) is not transmitted to the Governance Node (HC-133 is PLANNED), so no
 * decision can follow it.
 */

/** Where a request stands, as the researcher sees it. `expiring` and `expired` are approvals. */
export type RequestState = 'under_review' | 'approved' | 'expiring' | 'expired' | 'rejected'

export type TrackingStepId = 'submitted' | 'review' | 'decision'

export interface TrackingStep {
  id: TrackingStepId
  state: StepState
  /** When the step was reached (ISO 8601), if it was. */
  at: string | null
}

export interface TrackedRequest {
  summary: ProjectSummary
  request: ResearchAccessRequest
  /** The Governance decision on this request, displayed only. */
  decision: GovernanceDecision | null
  state: RequestState
  steps: TrackingStep[]
  /** Validity of an approval at the snapshot's time; null unless approved. */
  authorization: AuthorizationStatus | null
  /** The Governance reviewer named on the decision, if known. */
  decidedBy: StaffMember | null
  /**
   * False for a request submitted in this session: it stays in the portal and
   * never reaches the Governance / Ethics Authority.
   */
  transmitted: boolean
}

export interface RequestTracking {
  /** Requests needing the researcher's attention first (refused, expired), then under review, then approved. */
  requests: TrackedRequest[]
  /** Projects without an access request yet, most recent first. */
  unsubmitted: ProjectSummary[]
  counts: Record<RequestState, number>
}

const STATE_ORDER: Record<RequestState, number> = {
  rejected: 0,
  expired: 1,
  expiring: 2,
  under_review: 3,
  approved: 4,
}

function requestState(request: ResearchAccessRequest, decision: GovernanceDecision | null, authorization: AuthorizationStatus | null): RequestState {
  if (request.status === 'rejected' || decision?.outcome === 'rejected') return 'rejected'
  if (request.status === 'under_review' || !decision) return 'under_review'
  if (authorization?.state === 'expired') return 'expired'
  if (authorization?.state === 'expiring') return 'expiring'
  return 'approved'
}

function trackingSteps(request: ResearchAccessRequest, decision: GovernanceDecision | null, state: RequestState): TrackingStep[] {
  const decided = state !== 'under_review' && decision !== null
  return [
    { id: 'submitted', state: 'done', at: request.submittedAt },
    { id: 'review', state: decided ? 'done' : 'current', at: null },
    {
      id: 'decision',
      state: !decided ? 'upcoming' : state === 'rejected' || state === 'expired' ? 'blocked' : 'done',
      at: decided ? decision.decidedAt : null,
    },
  ]
}

/** Derives the researcher's request tracking at the snapshot's reference time. Pure. */
export function deriveRequestTracking(snapshot: ResearchSnapshot): RequestTracking {
  const now = new Date(snapshot.asOf)
  const fixtureIds = new Set(FIXTURE_ACCESS_REQUESTS.map((r) => r.id))

  const requests = snapshot.projects
    .flatMap((summary): TrackedRequest[] => {
      const { request } = summary
      if (!request) return []
      const decision = summary.decision?.subjectId === request.id ? summary.decision : null
      const authorization = authorizationStatus(summary, now)
      const state = requestState(request, decision, authorization)
      return [
        {
          summary,
          request,
          decision,
          state,
          steps: trackingSteps(request, decision, state),
          authorization,
          decidedBy: decision ? staffMemberById(decision.decidedById) : null,
          transmitted: fixtureIds.has(request.id),
        },
      ]
    })
    .sort(
      (a, b) =>
        STATE_ORDER[a.state] - STATE_ORDER[b.state] || b.request.submittedAt.localeCompare(a.request.submittedAt),
    )

  const counts: Record<RequestState, number> = { under_review: 0, approved: 0, expiring: 0, expired: 0, rejected: 0 }
  for (const r of requests) counts[r.state] += 1

  return {
    requests,
    unsubmitted: snapshot.projects
      .filter((s) => s.request === null)
      .sort((a, b) => b.project.createdAt.localeCompare(a.project.createdAt)),
    counts,
  }
}
