/**
 * Synchronization request list (HC-074, D1).
 *
 * Pure rules for the Governance Portal's list of inter-hospital synchronization
 * requests: the status a reviewer must see, the order, the filters, and readable labels.
 * Data comes from the canonical fictional fixtures; nothing here contacts a node.
 */
import type {
  ConsentInfo,
  GovernanceDecision,
  SynchronizationRequest,
} from '../types/governance'

/**
 * What the request means today. An approved request whose decision has lapsed is
 * `expired`: it no longer authorizes any exchange.
 */
export type SyncListStatus = 'pending' | 'active' | 'expired' | 'rejected'

export type SyncListFilter = 'all' | SyncListStatus

export const SYNC_FILTERS: readonly SyncListFilter[] = ['all', 'pending', 'active', 'expired', 'rejected']

export interface SyncListRow {
  request: SynchronizationRequest
  status: SyncListStatus
  /** End of the authorization for an approved request, if the decision sets one. */
  validUntil: string | null
}

// Pending requests need the reviewer first; then what still authorizes an exchange.
const STATUS_ORDER: Record<SyncListStatus, number> = {
  pending: 0,
  active: 1,
  expired: 2,
  rejected: 3,
}

export function syncListStatus(
  request: SynchronizationRequest,
  decision: GovernanceDecision | undefined,
  now: Date,
): SyncListStatus {
  if (request.status === 'pending') return 'pending'
  if (request.status === 'rejected') return 'rejected'
  const validUntil = decision?.validUntil
  return validUntil && new Date(validUntil) <= now ? 'expired' : 'active'
}

/** Rows ordered by what needs attention: status first, then newest submission. */
export function syncListRows(
  requests: readonly SynchronizationRequest[],
  decisionFor: (id: string | null) => GovernanceDecision | undefined,
  now: Date,
): SyncListRow[] {
  return requests
    .map((request) => {
      const decision = decisionFor(request.decisionId)
      return {
        request,
        status: syncListStatus(request, decision, now),
        validUntil: request.status === 'approved' ? (decision?.validUntil ?? null) : null,
      }
    })
    .sort(
      (a, b) =>
        STATUS_ORDER[a.status] - STATUS_ORDER[b.status] ||
        b.request.submittedAt.localeCompare(a.request.submittedAt),
    )
}

export function filterSyncRows(rows: readonly SyncListRow[], filter: SyncListFilter): SyncListRow[] {
  return filter === 'all' ? [...rows] : rows.filter((row) => row.status === filter)
}

export function countSyncRows(rows: readonly SyncListRow[]): Record<SyncListFilter, number> {
  const counts: Record<SyncListFilter, number> = { all: rows.length, pending: 0, active: 0, expired: 0, rejected: 0 }
  for (const row of rows) counts[row.status] += 1
  return counts
}

export const SYNC_STATUS_LABELS: Record<SyncListStatus, string> = {
  pending: 'En attente',
  active: 'Autorisée',
  expired: 'Expirée',
  rejected: 'Rejetée',
}

export const SYNC_FILTER_LABELS: Record<SyncListFilter, string> = {
  all: 'Toutes',
  pending: 'En attente',
  active: 'Autorisées',
  expired: 'Expirées',
  rejected: 'Rejetées',
}

const SCOPE_LABELS: Record<string, string> = {
  encounters: 'Consultations',
  medications: 'Médicaments',
  labReports: 'Analyses biologiques',
}

/** Unknown scope keys are shown as they are, never dropped. */
export function scopeLabel(scope: string): string {
  return SCOPE_LABELS[scope] ?? scope
}

const CONSENT_LABELS: Record<ConsentInfo['basis'], string> = {
  patient_grant: 'Autorisation du patient',
  signed_consent_form: 'Consentement signé',
  emergency_override: 'Dérogation d’urgence',
  none: 'Aucune autorisation',
}

export function consentLabel(basis: ConsentInfo['basis']): string {
  return CONSENT_LABELS[basis] ?? basis
}
