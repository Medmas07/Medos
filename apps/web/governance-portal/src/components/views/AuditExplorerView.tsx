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
  Table,
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
import type { LedgerProof } from '../../types/governance'

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
  const ledgerProofs = governanceService.getLedgerProofs()
  const [selectedProofId, setSelectedProofId] = useState<string>('proof-003')

  const selectedProof = ledgerProofs.find((p) => p.id === selectedProofId)

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

      {/* Ledger Proofs Card */}
      <Card
        title="Preuves Cryptographiques Ancrées (Registre Local Simulé)"
        actions={<DemoBadge>Simulé D1 — SHA-256</DemoBadge>}
        flush
      >
        <div className="px-5 py-3">
          <p className="text-xs text-slate-600">
            Ces preuves attestent de l'intégrité temporelle des décisions d'arbitrage de l'Autorité. Les empreintes sont calculées sur la représentation canonique des décisions.
          </p>
        </div>

        <Table<LedgerProof>
          caption="Preuves d'audit ancrées au registre"
          columns={[
            {
              key: 'proof-id',
              header: 'ID Preuve',
              render: (proof) => (
                <span className="font-mono text-xs font-semibold text-slate-800">{proof.id}</span>
              ),
            },
            {
              key: 'event-assoc',
              header: 'Événement d’Audit Associé',
              render: (proof) => (
                <div className="text-xs">
                  <span className="font-mono text-brand-700">{proof.auditEventId}</span>
                  <div className="text-slate-500">Décision: {proof.anchoredPayload.decisionId}</div>
                </div>
              ),
            },
            {
              key: 'hash',
              header: 'Empreinte Cryptographique (SHA-256)',
              render: (proof) => (
                <span className="block max-w-[280px] truncate font-mono text-xs text-slate-700" title={proof.hash}>
                  {proof.hash}
                </span>
              ),
            },
            {
              key: 'timestamp',
              header: 'Horodatage Ancrage',
              render: (proof) => (
                <span className="text-xs text-slate-600">
                  {new Date(proof.anchoredAt).toLocaleString('fr-TN', { dateStyle: 'short', timeStyle: 'medium' })}
                </span>
              ),
            },
            {
              key: 'status',
              header: 'Statut de Vérification',
              render: (proof) => (
                <Badge tone={proof.verificationStatus === 'verified' ? 'success' : 'danger'} dot>
                  {proof.verificationStatus === 'verified' ? 'Vérifié' : 'Altéré'}
                </Badge>
              ),
            },
            {
              key: 'action',
              header: 'Action',
              render: (proof) => (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={selectedProofId === proof.id ? 'primary' : 'ghost'}
                    onClick={() => setSelectedProofId(proof.id)}
                  >
                    Examiner
                  </Button>
                  {onInspectProof && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => onInspectProof(proof.id)}
                    >
                      Vérifier
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          rows={ledgerProofs}
          getRowKey={(item) => item.id}
        />

        {selectedProof && (
          <div className="border-t border-slate-200 bg-slate-50 p-4 text-xs">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <span className="font-semibold text-slate-900">
                Payload Minimisé Ancré ({selectedProof.id})
              </span>
              <span className="font-mono text-slate-500">Algorithme : {selectedProof.hashAlgorithm}</span>
            </div>
            <pre className="mt-2 overflow-x-auto rounded bg-white p-3 font-mono text-slate-800">
              {JSON.stringify(selectedProof.anchoredPayload, null, 2)}
            </pre>
            <p className="mt-2 text-slate-500">
              Note : Ce payload ne contient que des métadonnées structurelles d'arbitrage, respectant strictement le principe de minimisation des données.
            </p>
          </div>
        )}
      </Card>

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
