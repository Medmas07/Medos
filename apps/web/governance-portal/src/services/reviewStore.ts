/**
 * Local, in-memory state for SIMULATED governance decisions (HC-073, HC-076).
 *
 * Holds the decisions a reviewer records in this browser session, with their audit
 * events and the updated hospital applications or synchronization requests. Nothing is
 * sent to the Governance Node (HC-131, HC-132 are PLANNED) or to any Hospital Node, or
 * persisted: a page reload or reset returns to the canonical fixtures.
 */
import type {
  GovernanceAuditEvent,
  GovernanceDecision,
  HospitalApplication,
  SynchronizationRequest,
} from '../types/governance'
import type { RecordedReview } from './hospitalReview'
import type { RecordedSyncReview } from './syncReview'

export interface ReviewState {
  applications: Readonly<Record<string, HospitalApplication>>
  synchronizationRequests: Readonly<Record<string, SynchronizationRequest>>
  decisions: readonly GovernanceDecision[]
  auditEvents: readonly GovernanceAuditEvent[]
}

const initialState: ReviewState = {
  applications: {},
  synchronizationRequests: {},
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

  reset(): void {
    publish(initialState)
  },
}
