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

export function DataSyncView() {
  const syncs = governanceService.getSynchronizationRequests()
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')
  const [selectedSyncId, setSelectedSyncId] = useState<string>('sync-001')

  const filteredSyncs = syncs.filter((s) => {
    if (filter === 'all') return true
    return s.status === filter
  })

  const selectedSync = syncs.find((s) => s.id === selectedSyncId)
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
          <div className="flex gap-2">
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

      <Alert tone="info" title="Contrôle de finalité">
        Chaque synchronisation exige une finalité clinique explicite, une base d'autorisation vérifiée et une durée strictement délimitée. Aucun accès SQL direct entre serveurs hospitaliers n'est autorisé.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <Card title="File des Demandes de Synchronisation" flush>
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
                        <div className="font-medium text-slate-900">{pat ? `${pat.firstName} ${pat.lastName}` : s.patientId}</div>
                        <div className="text-xs text-slate-500">{pat?.federatedId} • {s.id}</div>
                      </div>
                    )
                  },
                },
                {
                  key: 'organizations',
                  header: 'Établissements (Demandeur → Cible)',
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
                  key: 'scope',
                  header: 'Périmètre & Durée',
                  render: (s) => (
                    <div className="text-xs">
                      <div className="flex flex-wrap gap-1">
                        {s.scope.map((scopeItem) => (
                          <Badge key={scopeItem} tone="neutral">{scopeItem}</Badge>
                        ))}
                      </div>
                      <span className="text-slate-500">{s.durationDays} jours</span>
                    </div>
                  ),
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
                    decision.outcome === 'approved'
                      ? 'border-success-200 bg-success-50 text-success-800'
                      : 'border-danger-200 bg-danger-50 text-danger-800'
                  }`}
                >
                  <div className="font-semibold">
                    Décision d'arbitrage : {decision.outcome === 'approved' ? 'Autorisée' : 'Refusée'}
                  </div>
                  <p className="mt-1">« {decision.rationale} »</p>
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
