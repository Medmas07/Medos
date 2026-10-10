/**
 * Local, in-memory state for SIMULATED governance decisions (HC-073).
 *
 * Holds the decisions a reviewer records in this browser session, with their audit
 * events and updated applications. Nothing is sent to the Governance Node (HC-131 is
 * PLANNED) or persisted: a page reload or reset returns to the canonical fixtures.
 */
import type {
  GovernanceAuditEvent,
  GovernanceDecision,
  HospitalApplication,
} from '../types/governance'
import type { RecordedReview } from './hospitalReview'

export interface ReviewState {
  applications: Readonly<Record<string, HospitalApplication>>
  decisions: readonly GovernanceDecision[]
  auditEvents: readonly GovernanceAuditEvent[]
}

const initialState: ReviewState = { applications: {}, decisions: [], auditEvents: [] }

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
      applications: { ...state.applications, [review.application.id]: review.application },
      decisions: [...state.decisions, review.decision],
      auditEvents: [...state.auditEvents, review.auditEvent],
    })
  },

  reset(): void {
    publish(initialState)
  },
}
