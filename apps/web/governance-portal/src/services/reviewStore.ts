/**
 * Local, in-memory state for SIMULATED governance decisions (HC-073, HC-076, HC-078).
 *
 * Holds the decisions a reviewer records in this browser session, with their audit
 * events and the updated hospital applications, synchronization requests, or research
 * access requests. Nothing is sent to the Governance Node (HC-131 to HC-133 are PLANNED) or to any Hospital Node, or
 * persisted: a page reload or reset returns to the canonical fixtures.
 */
import type {
  GovernanceAuditEvent,
  GovernanceDecision,
  HospitalApplication,
  ResearchAccessRequest,
  SynchronizationRequest,
} from '../types/governance'
import type { RecordedReview } from './hospitalReview'
import type { RecordedResearchReview } from './researchReview'
import type { RecordedSyncReview } from './syncReview'

export interface ReviewState {
  applications: Readonly<Record<string, HospitalApplication>>
  synchronizationRequests: Readonly<Record<string, SynchronizationRequest>>
  researchAccessRequests: Readonly<Record<string, ResearchAccessRequest>>
  decisions: readonly GovernanceDecision[]
  auditEvents: readonly GovernanceAuditEvent[]
}

const initialState: ReviewState = {
  applications: {},
  synchronizationRequests: {},
  researchAccessRequests: {},
  decisions: [],
  auditEvents: [],
}

let state = initialState
const listeners = new Set<() => void>()

function publish(next: ReviewState) {
  state = next
  listeners.forEach((listener) => listener())
}

export const reviewStore = {
  getSnapshot(): ReviewState {
    return state
  },

  subscribe(listener: () => void): () => void {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },

  /** Sequence number for the next simulated decision. */
  nextSequence(): number {
    return state.decisions.length + 1
  },

  record(review: RecordedReview): void {
    publish({
      ...state,
      applications: { ...state.applications, [review.application.id]: review.application },
      decisions: [...state.decisions, review.decision],
      auditEvents: [...state.auditEvents, review.auditEvent],
    })
  },

  recordSync(review: RecordedSyncReview): void {
    publish({
      ...state,
      synchronizationRequests: {
        ...state.synchronizationRequests,
        [review.request.id]: review.request,
      },
      decisions: [...state.decisions, review.decision],
      auditEvents: [...state.auditEvents, review.auditEvent],
    })
  },

  recordResearch(review: RecordedResearchReview): void {
    publish({
      ...state,
      researchAccessRequests: {
        ...state.researchAccessRequests,
        [review.request.id]: review.request,
      },
      decisions: [...state.decisions, review.decision],
      auditEvents: [...state.auditEvents, review.auditEvent],
    })
  },

  reset(): void {
    publish(initialState)
  },
}
