/**
 * Research access request list (HC-077, D1).
 *
 * Pure rules for the Governance Portal's list of research access requests:
 * status resolution as of today, ordering (attention-first), filtering, and counts.
 * Data comes from canonical fixtures; no cross-context persistence access.
 */
import type {
  GovernanceDecision,
  ResearchAccessRequest,
  ResearchProjectInfo,
} from '../types/governance'

export type ResearchListStatus = 'under_review' | 'active' | 'expired' | 'rejected'

export type ResearchListFilter = 'all' | ResearchListStatus

export const RESEARCH_FILTERS: readonly ResearchListFilter[] = [
  'all',
  'under_review',
  'active',
  'expired',
  'rejected',
]

export interface ResearchListRow {
  request: ResearchAccessRequest
  project: ResearchProjectInfo | undefined
  status: ResearchListStatus
  validUntil: string | null
}

// Under review requests need the ethics reviewer first; then active ones.
const STATUS_ORDER: Record<ResearchListStatus, number> = {
  under_review: 0,
  active: 1,
  expired: 2,
  rejected: 3,
}

export function researchListStatus(
  request: ResearchAccessRequest,
  decision: GovernanceDecision | undefined,
  now: Date,
): ResearchListStatus {
  if (request.status === 'under_review') return 'under_review'
  if (request.status === 'rejected') return 'rejected'
  const validUntil = decision?.validUntil
  return validUntil && new Date(validUntil) <= now ? 'expired' : 'active'
}

/** Rows ordered by what needs attention: status first, then newest submission. */
export function researchListRows(
  requests: readonly ResearchAccessRequest[],
  projectFor: (projectId: string) => ResearchProjectInfo | undefined,
  decisionFor: (id: string | null) => GovernanceDecision | undefined,
  now: Date,
): ResearchListRow[] {
  return requests
    .map((request) => {
      const decision = decisionFor(request.decisionId)
      return {
        request,
        project: projectFor(request.projectId),
        status: researchListStatus(request, decision, now),
        validUntil: request.status === 'approved' ? (decision?.validUntil ?? null) : null,
      }
    })
    .sort(
      (a, b) =>
        STATUS_ORDER[a.status] - STATUS_ORDER[b.status] ||
        b.request.submittedAt.localeCompare(a.request.submittedAt),
    )
}

export function filterResearchRows(
  rows: readonly ResearchListRow[],
  filter: ResearchListFilter,
): ResearchListRow[] {
  return filter === 'all' ? [...rows] : rows.filter((row) => row.status === filter)
}

export function countResearchRows(
  rows: readonly ResearchListRow[],
): Record<ResearchListFilter, number> {
  const counts: Record<ResearchListFilter, number> = {
    all: rows.length,
    under_review: 0,
    active: 0,
    expired: 0,
    rejected: 0,
  }
  for (const row of rows) counts[row.status] += 1
  return counts
}

export const RESEARCH_STATUS_LABELS: Record<ResearchListStatus, string> = {
  under_review: 'En examen',
  active: 'Autorisée',
  expired: 'Expirée',
  rejected: 'Rejetée',
}

export const RESEARCH_FILTER_LABELS: Record<ResearchListFilter, string> = {
  all: 'Toutes',
  under_review: 'En examen',
  active: 'Autorisées',
  expired: 'Expirées',
  rejected: 'Rejetées',
}
