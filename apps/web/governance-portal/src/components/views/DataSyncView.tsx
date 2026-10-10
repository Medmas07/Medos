import { useState, useSyncExternalStore } from 'react'
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
import { reviewStore } from '../../services/reviewStore'
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
import { SyncReviewForm } from '../review/SyncReviewForm'
import { SyncRequestDetail } from '../sync/SyncRequestDetail'

/** The reviewer signed in to this demo portal (fictional, HC-005). */
const REVIEWER_ID = 'usr-olfa'

const STATUS_TONES: Record<SyncListStatus, Tone> = {
  pending: 'warning',
  active: 'success',
  expired: 'neutral',
  rejected: 'danger',
}

const formatDate = (iso: string) => new Date(iso).toLocaleDateString('fr-TN')

export function DataSyncView() {
  // Re-render when a simulated decision is recorded or the demo is reset (HC-076).
  const reviewState = useSyncExternalStore(reviewStore.subscribe, reviewStore.getSnapshot)
  const simulatedSyncCount = Object.keys(reviewState.synchronizationRequests).length

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
  const decision = selectedSync ? governanceService.getDecision(selectedSync.decisionId) : undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Flux d'Interopérabilité Sécurisés"
        title="Synchronisations Inter-Hospitalières de Soins"
        description="Autorisation et gouvernance des échanges ciblés entre établissements hospitaliers pour la continuité du parcours de soins."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {simulatedSyncCount > 0 && (
              <Button variant="ghost" size="sm" onClick={() => reviewStore.reset()}>
                Réinitialiser la démo
              </Button>
            )}
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
          </div>
        }
      />

      <Alert tone="info" title="Contrôle de finalité & Souveraineté hospitalière">
        Chaque synchronisation exige une finalité clinique explicite, une base d'autorisation vérifiée et une durée strictement délimitée. Aucun accès SQL direct entre serveurs hospitaliers n'est autorisé.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Table of synchronization requests */}
        <div className="lg:col-span-5">
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
                        <div className="text-slate-500">Durée : {request.durationDays} j</div>
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
                          <div className="text-slate-500 text-[10px]">
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

        {/* Detailed view of selected request */}
        <div className="lg:col-span-7">
          {selectedSync ? (
            <SyncRequestDetail
              request={selectedSync}
              reviewForm={
                !decision && selectedSync.status === 'pending' ? (
                  <SyncReviewForm
                    key={selectedSync.id}
                    context={{
                      request: selectedSync,
                      requester: reqOrg,
                      target: tgtOrg,
                      grant: governanceService.getAccessGrant(selectedSync.consent.accessGrantId),
                    }}
                    reviewer={governanceService.getPerson(REVIEWER_ID)}
                    reviewerName={governanceService.getPersonName(REVIEWER_ID)}
                  />
                ) : undefined
              }
            />
          ) : (
            <Card>
              <div className="py-12 text-center text-xs text-slate-500">
                Sélectionnez une demande dans la liste pour examiner ses détails.
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
