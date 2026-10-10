import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  PageHeader,
  Table,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import type { GovernanceAuditEvent, LedgerProof } from '../../types/governance'

interface AuditExplorerViewProps {
  onInspectProof?: (proofId: string) => void
}

export function AuditExplorerView({ onInspectProof }: AuditExplorerViewProps) {
  const auditEvents = governanceService.getAuditEvents()
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

      {/* Audit Events Table */}
      <Card title="Journal Exhaustif des Événements d'Audit" flush>
        <Table<GovernanceAuditEvent>
          caption="Journal complet des événements d'audit"
          columns={[
            {
              key: 'timestamp',
              header: 'Horodatage',
              render: (evt) => (
                <span className="font-mono text-xs text-slate-600">
                  {new Date(evt.at).toLocaleString('fr-TN', { dateStyle: 'short', timeStyle: 'medium' })}
                </span>
              ),
            },
            {
              key: 'event-id',
              header: 'ID Événement',
              render: (evt) => (
                <span className="font-mono text-xs text-slate-800">{evt.id}</span>
              ),
            },
            {
              key: 'actor',
              header: 'Acteur',
              render: (evt) => (
                <span className="text-xs text-slate-700">
                  {governanceService.getPersonName(evt.actorId)}
                </span>
              ),
            },
            {
              key: 'action',
              header: 'Action',
              render: (evt) => (
                <Badge tone="neutral">
                  {evt.action}
                </Badge>
              ),
            },
            {
              key: 'subject',
              header: 'Objet Concerné',
              render: (evt) => (
                <div className="text-xs">
                  <span className="font-semibold text-slate-800">{evt.subjectId}</span>
                  <span className="ml-1.5 text-slate-500">({evt.subjectType})</span>
                </div>
              ),
            },
            {
              key: 'organizations',
              header: 'Organisations',
              render: (evt) => (
                <div className="flex flex-wrap gap-1">
                  {evt.organizationIds.map((orgId) => {
                    const org = governanceService.getOrganization(orgId)
                    return (
                      <span key={orgId} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-700">
                        {org?.shortName ?? orgId}
                      </span>
                    )
                  })}
                </div>
              ),
            },
          ]}
          rows={auditEvents}
          getRowKey={(item) => item.id}
        />
      </Card>
    </div>
  )
}
