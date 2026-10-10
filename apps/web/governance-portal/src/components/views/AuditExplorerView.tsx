import { useState, useSyncExternalStore } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  Timeline,
  type TimelineItem,
  type Tone,
} from '@hackcure/design-system'
import {
  AUDIT_DOMAIN_FILTERS,
  AUDIT_DOMAIN_LABELS,
  auditTimeline,
  countByDomain,
  filterTimeline,
  involvedOrganizationIds,
  type AuditDomainFilter,
  type AuditTimelineEntry,
} from '../../services/auditTimeline'
import { governanceService } from '../../services/governanceService'
import { reviewStore } from '../../services/reviewStore'
import { ProofExplorer } from '../ledger/ProofExplorer'

const formatDateTime = (iso: string) =>
  new Date(iso).toLocaleString('fr-TN', { dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23' })

interface AuditExplorerViewProps {
  onInspectProof?: (proofId: string) => void
}

export function AuditExplorerView({ onInspectProof }: AuditExplorerViewProps) {
  // Re-render when a simulated decision adds an event or the demo is reset.
  useSyncExternalStore(reviewStore.subscribe, reviewStore.getSnapshot)
  const [domain, setDomain] = useState<AuditDomainFilter>('all')
  const [organizationId, setOrganizationId] = useState<string | null>(null)

  const entries = auditTimeline(governanceService.getAuditEvents(), {
    decision: (id) => governanceService.getDecision(id),
    proofForEvent: (id) => governanceService.getProofForEvent(id),
  })
  const counts = countByDomain(entries)
  const visible = filterTimeline(entries, { domain, organizationId })
  const orgName = (id: string) => governanceService.getOrganization(id)?.shortName ?? id

  const toItem = (entry: AuditTimelineEntry): TimelineItem => ({
    id: entry.event.id,
    title: entry.title,
    timestamp: formatDateTime(entry.event.at),
    dateTime: entry.event.at,
    tone: (entry.simulated ? 'demo' : entry.tone) as Tone,
    description: (
      <span className="text-xs">
        <span className="font-mono text-slate-800">{entry.subjectRef}</span>
        {' • '}
        {entry.event.actorId ? `par ${governanceService.getPersonName(entry.event.actorId)}` : 'reçue automatiquement'}
        <span className="font-mono text-slate-400"> • {entry.event.id}</span>
      </span>
    ),
    meta: (
      <>
        {entry.event.organizationIds.map((id) => (
          <Badge key={id} tone="neutral">{orgName(id)}</Badge>
        ))}
        {entry.simulated ? (
          <DemoBadge>Simulé — non persisté</DemoBadge>
        ) : entry.proof ? (
          <>
            <Badge tone="success" dot>Preuve ancrée {entry.proof.id}</Badge>
            {onInspectProof && (
              <Button size="sm" variant="ghost" onClick={() => onInspectProof(entry.proof!.id)}>
                Vérifier
              </Button>
            )}
          </>
        ) : (
          <span className="text-xs text-slate-400">Non ancré</span>
        )}
      </>
    ),
  })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Immuabilité & Conformité"
        title="Journal d'Audit et Preuves de Registre"
        description="Traçabilité complète des événements de gouvernance et vérification des preuves cryptographiques ancrées."
      />

      <Alert tone="warning" title="Règle d'or de confidentialité">
        Le registre blockchain stocke uniquement des preuves cryptographiques minimisées (identifiants, horodatages, empreintes de décision SHA-256). Aucune donnée patient, aucun diagnostic et aucun dossier médical ne figure sur la blockchain.
      </Alert>

      {/* MOCKED BLOCKCHAIN proof explorer (HC-080) */}
      <ProofExplorer onInspectProof={onInspectProof} />

      {/* Audit timeline (HC-079) */}
      <Card
        title="Chronologie de l'Audit de Gouvernance"
        actions={<span className="text-xs text-slate-500">Du plus récent au plus ancien</span>}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600">
            Événements minimisés du Nœud de Gouvernance : références, acteurs et organisations, jamais de donnée patient ni clinique. Chaque Nœud Hospitalier tient sa propre piste d'audit des accès aux données.
          </p>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrer par domaine">
              {AUDIT_DOMAIN_FILTERS.map((f) => (
                <Button
                  key={f}
                  size="sm"
                  variant={domain === f ? 'primary' : 'secondary'}
                  aria-pressed={domain === f}
                  onClick={() => setDomain(f)}
                >
                  {AUDIT_DOMAIN_LABELS[f]} ({counts[f]})
                </Button>
              ))}
            </div>
            <div className="w-full sm:w-64">
              <SelectField
                label="Organisation"
                placeholder="Toutes les organisations"
                value={organizationId ?? ''}
                onChange={(e) => setOrganizationId(e.target.value || null)}
                options={involvedOrganizationIds(entries).map((id) => ({ value: id, label: orgName(id) }))}
              />
            </div>
          </div>

          {visible.length === 0 ? (
            <EmptyState
              title="Aucun événement pour ces filtres"
              description="Aucun événement d'audit ne correspond au domaine et à l'organisation choisis."
              action={
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setDomain('all')
                    setOrganizationId(null)
                  }}
                >
                  Afficher tous les événements
                </Button>
              }
            />
          ) : (
            <Timeline label="Chronologie des événements d'audit de gouvernance" items={visible.map(toItem)} />
          )}
        </div>
      </Card>
    </div>
  )
}
