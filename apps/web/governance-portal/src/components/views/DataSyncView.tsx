import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Table,
  type Tone,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import {
  SYNC_FILTERS,
  SYNC_FILTER_LABELS,
  SYNC_STATUS_LABELS,
  consentLabel,
  countSyncRows,
  filterSyncRows,
  scopeLabel,
  syncListRows,
  type SyncListFilter,
  type SyncListRow,
  type SyncListStatus,
} from '../../services/syncRequestList'

const STATUS_TONES: Record<SyncListStatus, Tone> = {
  pending: 'warning',
  active: 'success',
  expired: 'neutral',
  rejected: 'danger',
}

const formatDate = (iso: string) => new Date(iso).toLocaleDateString('fr-TN')

export function DataSyncView() {
  // Statuses are evaluated once per visit: an authorization that has lapsed shows as expired.
  const [now] = useState(() => new Date())
  const rows = syncListRows(
    governanceService.getSynchronizationRequests(),
    (id) => governanceService.getDecision(id),
    now,
  )
  const counts = countSyncRows(rows)
  const [filter, setFilter] = useState<SyncListFilter>('all')
  const [selectedSyncId, setSelectedSyncId] = useState<string>('sync-001')

  const filteredRows = filterSyncRows(rows, filter)

  const selectedRow = rows.find((row) => row.request.id === selectedSyncId)
  const selectedSync = selectedRow?.request
  const reqOrg = selectedSync ? governanceService.getOrganization(selectedSync.requesterOrganizationId) : undefined
  const tgtOrg = selectedSync ? governanceService.getOrganization(selectedSync.targetOrganizationId) : undefined
  const patient = selectedSync ? governanceService.getPatient(selectedSync.patientId) : undefined
  const decision = selectedSync ? governanceService.getDecision(selectedSync.decisionId) : undefined
  const proof = decision ? governanceService.getProofForEvent(
    governanceService.getAuditEvents().find((e) => e.subjectId === decision.id)?.id ?? ''
  ) : undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Flux d'Interopérabilité Sécurisés"
        title="Synchronisations Inter-Hospitalières de Soins"
        description="Autorisation et gouvernance des échanges ciblés entre établissements hospitaliers pour la continuité du parcours de soins."
        actions={
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrer par statut">
            {SYNC_FILTERS.map((f) => (
              <Button
                key={f}
                variant={filter === f ? 'primary' : 'secondary'}
                size="sm"
                aria-pressed={filter === f}
                onClick={() => setFilter(f)}
              >
                {SYNC_FILTER_LABELS[f]} ({counts[f]})
              </Button>
            ))}
          </div>
        }
      />

      <Alert tone="info" title="Contrôle de finalité">
        Chaque synchronisation exige une finalité clinique explicite, une base d'autorisation vérifiée et une durée strictement délimitée. Aucun accès SQL direct entre serveurs hospitaliers n'est autorisé.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <Card title="File des Demandes de Synchronisation" flush>
            {filteredRows.length === 0 ? (
              <EmptyState
                title={`Aucune demande « ${SYNC_FILTER_LABELS[filter].toLowerCase()} »`}
                description="Aucune demande de synchronisation ne correspond à ce filtre."
                action={
                  <Button size="sm" variant="secondary" onClick={() => setFilter('all')}>
                    Afficher toutes les demandes
                  </Button>
                }
              />
            ) : (
              <Table<SyncListRow>
                caption="Demandes de synchronisation clinique inter-hospitalière, les demandes en attente en premier"
                columns={[
                  {
                    key: 'request',
                    header: 'Demande',
                    render: ({ request }) => {
                      const r = governanceService.getOrganization(request.requesterOrganizationId)
                      const t = governanceService.getOrganization(request.targetOrganizationId)
                      return (
                        <div className="space-y-0.5 text-xs">
                          <div className="font-mono font-semibold text-slate-800">{request.id}</div>
                          <div className="font-medium text-slate-800">
                            {r?.shortName ?? request.requesterOrganizationId}
                            <span className="text-slate-500"> → {t?.shortName ?? request.targetOrganizationId}</span>
                          </div>
                          <div className="text-slate-500">
                            <span title="Identifiant fédéré pseudonyme du patient">
                              {governanceService.getPatient(request.patientId)?.federatedId ?? request.patientId}
                            </span>
                            {' • '}Reçue le {formatDate(request.submittedAt)}
                          </div>
                        </div>
                      )
                    },
                  },
                  {
                    key: 'purpose',
                    header: 'Finalité & Périmètre',
                    render: ({ request }) => (
                      <div className="space-y-1 text-xs">
                        <div className="line-clamp-2 text-slate-800" title={request.purpose}>{request.purpose}</div>
                        <div className="flex flex-wrap gap-1">
                          {request.scope.map((item) => (
                            <Badge key={item} tone="neutral">{scopeLabel(item)}</Badge>
                          ))}
                          <Badge tone={request.consent.basis === 'none' ? 'danger' : 'info'}>
                            {consentLabel(request.consent.basis)}
                          </Badge>
                        </div>
                        <div className="text-slate-500">Durée demandée : {request.durationDays} jours</div>
                      </div>
                    ),
                  },
                  {
                    key: 'status',
                    header: 'Statut',
                    render: ({ status, validUntil }) => (
                      <div className="space-y-0.5 text-xs">
                        <Badge tone={STATUS_TONES[status]} dot>{SYNC_STATUS_LABELS[status]}</Badge>
                        {validUntil && (
                          <div className="text-slate-500">
                            {status === 'expired' ? 'Expirée le' : "Jusqu'au"} {formatDate(validUntil)}
                          </div>
                        )}
                      </div>
                    ),
                  },
                  {
                    key: 'action',
                    header: 'Action',
                    render: ({ request }) => (
                      <Button
                        size="sm"
                        variant={selectedSyncId === request.id ? 'primary' : 'ghost'}
                        aria-pressed={selectedSyncId === request.id}
                        onClick={() => setSelectedSyncId(request.id)}
                      >
                        {selectedSyncId === request.id ? 'Actif' : 'Voir'}
                      </Button>
                    ),
                  },
                ]}
                rows={filteredRows}
                getRowKey={(row) => row.request.id}
              />
            )}
          </Card>
        </div>

        <div className="lg:col-span-5">
          {selectedSync ? (
            <Card title={`Détail : ${selectedSync.id}`} className="space-y-4">
              <div className="space-y-2 text-xs">
                <div>
                  <span className="font-semibold text-slate-700">Finalité déclarée :</span>
                  <p className="mt-0.5 rounded bg-slate-50 p-2 text-slate-800">{selectedSync.purpose}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2">
                  <div className="rounded bg-slate-50 p-2">
                    <span className="text-slate-500">Demandeur :</span>
                    <p className="font-medium text-slate-800">{reqOrg?.name}</p>
                  </div>
                  <div className="rounded bg-slate-50 p-2">
                    <span className="text-slate-500">Détenteur des données :</span>
                    <p className="font-medium text-slate-800">{tgtOrg?.name}</p>
                  </div>
                </div>

                <div className="rounded bg-slate-50 p-2">
                  <span className="text-slate-500">Base d'autorisation :</span>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge tone={selectedSync.consent.basis === 'none' ? 'danger' : 'info'}>
                      {selectedSync.consent.basis === 'patient_grant' && 'Autorisation patiente active'}
                      {selectedSync.consent.basis === 'signed_consent_form' && 'Formulaire signé vérifié'}
                      {selectedSync.consent.basis === 'none' && 'Aucune autorisation fournie'}
                    </Badge>
                    {selectedSync.consent.accessGrantId && (
                      <span className="font-mono text-slate-600">Réf: {selectedSync.consent.accessGrantId}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Decision details */}
              {decision ? (
                <div
                  className={`rounded-md border p-3 text-xs ${
                    selectedRow?.status === 'expired'
                      ? 'border-slate-200 bg-slate-50 text-slate-800'
                      : decision.outcome === 'approved'
                      ? 'border-success-200 bg-success-50 text-success-800'
                      : 'border-danger-200 bg-danger-50 text-danger-800'
                  }`}
                >
                  <div className="font-semibold">
                    Décision d'arbitrage : {decision.outcome === 'approved' ? 'Autorisée' : 'Refusée'}
                    {selectedRow?.status === 'expired' && ' — expirée'}
                  </div>
                  <p className="mt-1">« {decision.rationale} »</p>
                  {selectedRow?.status === 'expired' && selectedRow.validUntil && (
                    <p className="mt-1 font-medium text-slate-700">
                      Autorisation expirée le {formatDate(selectedRow.validUntil)} : elle ne permet plus aucun échange.
                    </p>
                  )}
                  {decision.conditions.length > 0 && (
                    <div className="mt-2">
                      <span className="font-medium">Conditions imposées :</span>
                      <ul className="mt-1 list-disc pl-4">
                        {decision.conditions.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {proof && (
                    <div className="mt-2 flex items-center gap-1.5 border-t border-success-200/60 pt-2 font-mono text-[11px]">
                      <span className="text-slate-600">Empreinte ancrée :</span>
                      <span className="truncate">{proof.hash}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs">
                  <div className="font-semibold text-amber-900">Demande en cours d'instruction</div>
                  <p className="mt-1 text-amber-800">
                    L'Autorité vérifie la conformité de la finalité et le consentement du patient ({patient?.federatedId}) avant émission du jeton d'autorisation fédéré.
                  </p>
                </div>
              )}
            </Card>
          ) : (
            <Card>
              <div className="py-8 text-center text-xs text-slate-500">
                Sélectionnez une demande pour examiner ses détails.
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
