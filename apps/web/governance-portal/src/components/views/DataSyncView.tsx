import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  PageHeader,
  Table,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import type { SynchronizationRequest } from '../../types/governance'
import { SyncRequestDetail } from '../sync/SyncRequestDetail'

export function DataSyncView() {
  const syncs = governanceService.getSynchronizationRequests()
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')
  const [selectedSyncId, setSelectedSyncId] = useState<string>('sync-001')

  const filteredSyncs = syncs.filter((s) => {
    if (filter === 'all') return true
    return s.status === filter
  })

  const selectedSync = syncs.find((s) => s.id === selectedSyncId)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Flux d'Interopérabilité Sécurisés"
        title="Synchronisations Inter-Hospitalières de Soins"
        description="Autorisation et gouvernance des échanges ciblés entre établissements hospitaliers pour la continuité du parcours de soins."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant={filter === 'all' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('all')}
            >
              Toutes ({syncs.length})
            </Button>
            <Button
              variant={filter === 'pending' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('pending')}
            >
              En attente ({syncs.filter((s) => s.status === 'pending').length})
            </Button>
            <Button
              variant={filter === 'approved' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('approved')}
            >
              Approuvées ({syncs.filter((s) => s.status === 'approved').length})
            </Button>
            <Button
              variant={filter === 'rejected' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('rejected')}
            >
              Rejetées ({syncs.filter((s) => s.status === 'rejected').length})
            </Button>
          </div>
        }
      />

      <Alert tone="info" title="Contrôle de finalité & Souveraineté hospitalière">
        Chaque synchronisation exige une finalité clinique explicite, une base d'autorisation vérifiée et une durée strictement délimitée. Aucun accès SQL direct entre serveurs hospitaliers n'est autorisé.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Table list of synchronization requests */}
        <div className="lg:col-span-5">
          <Card title="Demandes de Synchronisation" flush>
            <Table<SynchronizationRequest>
              caption="Demandes de synchronisation clinique inter-hospitalière"
              columns={[
                {
                  key: 'patient',
                  header: 'Réf. & Patient',
                  render: (s) => {
                    const pat = governanceService.getPatient(s.patientId)
                    return (
                      <div>
                        <div className="font-medium text-slate-900">
                          {pat ? `${pat.firstName} ${pat.lastName}` : s.patientId}
                        </div>
                        <div className="text-xs text-slate-500 font-mono">
                          {pat?.federatedId ?? s.patientId} • {s.id}
                        </div>
                      </div>
                    )
                  },
                },
                {
                  key: 'organizations',
                  header: 'Établissements',
                  render: (s) => {
                    const r = governanceService.getOrganization(s.requesterOrganizationId)
                    const t = governanceService.getOrganization(s.targetOrganizationId)
                    return (
                      <div className="text-xs">
                        <div className="font-semibold text-slate-800">{r?.shortName ?? s.requesterOrganizationId}</div>
                        <div className="text-slate-500">→ {t?.shortName ?? s.targetOrganizationId}</div>
                      </div>
                    )
                  },
                },
                {
                  key: 'status',
                  header: 'Statut',
                  render: (s) => {
                    if (s.status === 'pending') return <Badge tone="warning" dot>En attente</Badge>
                    if (s.status === 'approved') return <Badge tone="success" dot>Approuvée</Badge>
                    return <Badge tone="danger" dot>Rejetée</Badge>
                  },
                },
                {
                  key: 'action',
                  header: 'Action',
                  render: (s) => (
                    <Button
                      size="sm"
                      variant={selectedSyncId === s.id ? 'primary' : 'ghost'}
                      onClick={() => setSelectedSyncId(s.id)}
                    >
                      {selectedSyncId === s.id ? 'Actif' : 'Voir'}
                    </Button>
                  ),
                },
              ]}
              rows={filteredSyncs}
              getRowKey={(item) => item.id}
            />
          </Card>
        </div>

        {/* Detailed view of selected request */}
        <div className="lg:col-span-7">
          {selectedSync ? (
            <SyncRequestDetail request={selectedSync} />
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
