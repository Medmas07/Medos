/**
 * Governance audit timeline (HC-079, D1).
 *
 * Pure rules turning the Governance Node's minimized audit events into a readable,
 * newest-first timeline: what happened, to which request, with which outcome, by whom,
 * involving which organizations, and whether a ledger proof anchors it. Events carry
 * references only; this module never adds patient or clinical data. Hospital Nodes keep
 * their own audit trails (HC-116); nothing here centralizes them.
 */
import type {
  GovernanceAuditEvent,
  GovernanceDecision,
  LedgerProof,
  SubjectType,
} from '../types/governance'

export type AuditDomain = 'hospital' | 'synchronization' | 'research'

export type AuditDomainFilter = 'all' | AuditDomain

export const AUDIT_DOMAIN_FILTERS: readonly AuditDomainFilter[] = ['all', 'hospital', 'synchronization', 'research']

export const AUDIT_DOMAIN_LABELS: Record<AuditDomainFilter, string> = {
  all: 'Tous',
  hospital: 'Adhésions',
  synchronization: 'Synchronisations',
  research: 'Recherche',
}

export type AuditTone = 'success' | 'danger' | 'info' | 'neutral'

export interface AuditTimelineEntry {
  event: GovernanceAuditEvent
  /** Null when the event's subject cannot be resolved; it is still listed. */
  domain: AuditDomain | null
  title: string
  /** Reference of the request the event is about, such as sync-001. */
  subjectRef: string
  outcome: GovernanceDecision['outcome'] | null
  tone: AuditTone
  proof: LedgerProof | undefined
  simulated: boolean
}

export interface AuditLookups {
  decision: (id: string) => GovernanceDecision | undefined
  proofForEvent: (eventId: string) => LedgerProof | undefined
}

const DOMAIN_OF: Partial<Record<SubjectType, AuditDomain>> = {
  hospital_application: 'hospital',
  synchronization_request: 'synchronization',
  research_access_request: 'research',
}

const SUBJECT_NOUNS: Record<AuditDomain, string> = {
  hospital: 'adhésion',
  synchronization: 'synchronisation',
  research: 'accès recherche',
}

const OUTCOME_WORDS: Record<GovernanceDecision['outcome'], string> = {
  approved: 'approuvée',
  rejected: 'rejetée',
}

export function timelineEntry(event: GovernanceAuditEvent, lookups: AuditLookups): AuditTimelineEntry {
  const base = {
    event,
    proof: lookups.proofForEvent(event.id),
    simulated: Boolean(event.simulated),
  }
  if (event.action === 'decision_recorded' && event.subjectType === 'decision') {
    const decision = lookups.decision(event.subjectId)
    const domain = decision ? (DOMAIN_OF[decision.subjectType] ?? null) : null
    if (decision && domain) {
      return {
        ...base,
        domain,
        title: `Décision : ${SUBJECT_NOUNS[domain]} ${OUTCOME_WORDS[decision.outcome]}`,
        subjectRef: decision.subjectId,
        outcome: decision.outcome,
        tone: decision.outcome === 'approved' ? 'success' : 'danger',
      }
    }
    return { ...base, domain: null, title: 'Décision enregistrée', subjectRef: event.subjectId, outcome: null, tone: 'neutral' }
  }
  const domain = DOMAIN_OF[event.subjectType] ?? null
  const titles: Record<GovernanceAuditEvent['action'], string> = {
    application_submitted: 'Demande d’adhésion déposée',
    request_received: domain ? `Demande de ${SUBJECT_NOUNS[domain]} reçue` : 'Demande reçue',
    proof_verified: 'Preuve vérifiée',
    decision_recorded: 'Décision enregistrée',
  }
  return {
    ...base,
    domain,
    title: titles[event.action] ?? event.action,
    subjectRef: event.subjectId,
    outcome: null,
    tone: 'info',
  }
}

/** Newest first; events at the same instant keep a stable order by id. */
export function auditTimeline(
  events: readonly GovernanceAuditEvent[],
  lookups: AuditLookups,
): AuditTimelineEntry[] {
  return events
    .map((event) => timelineEntry(event, lookups))
    .sort(
      (a, b) =>
        new Date(b.event.at).getTime() - new Date(a.event.at).getTime() ||
        b.event.id.localeCompare(a.event.id),
    )
}

export interface AuditTimelineFilter {
  domain: AuditDomainFilter
  /** Only events involving this organization; null for all. */
  organizationId: string | null
}

export function filterTimeline(
  entries: readonly AuditTimelineEntry[],
  filter: AuditTimelineFilter,
): AuditTimelineEntry[] {
  return entries.filter(
    (entry) =>
      (filter.domain === 'all' || entry.domain === filter.domain) &&
      (filter.organizationId === null || entry.event.organizationIds.includes(filter.organizationId)),
  )
}

export function countByDomain(entries: readonly AuditTimelineEntry[]): Record<AuditDomainFilter, number> {
  const counts: Record<AuditDomainFilter, number> = { all: entries.length, hospital: 0, synchronization: 0, research: 0 }
  for (const entry of entries) if (entry.domain) counts[entry.domain] += 1
  return counts
}

/** Organizations that appear in at least one event, in first-seen order. */
export function involvedOrganizationIds(entries: readonly AuditTimelineEntry[]): string[] {
  return [...new Set(entries.flatMap((entry) => entry.event.organizationIds))]
}
