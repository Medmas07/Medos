import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  DemoBadge,
  PageHeader,
  Table,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import type { HospitalApplication } from '../../types/governance'

export function HospitalOnboardingView() {
  const applications = governanceService.getHospitalApplications()
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved'>('all')
  const [selectedAppId, setSelectedAppId] = useState<string>('app-hospital-c')

  const filteredApps = applications.filter((app) => {
    if (filter === 'pending') return app.status === 'human_review' || app.status === 'pending'
    if (filter === 'approved') return app.status === 'approved'
    return true
  })

  const selectedApp = applications.find((a) => a.id === selectedAppId)
  const selectedOrg = selectedApp ? governanceService.getOrganization(selectedApp.organizationId) : undefined
  const selectedDecision = selectedApp ? governanceService.getDecision(selectedApp.decisionId) : undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Gouvernance des Nœuds Hospitaliers"
        title="Dossiers d'Adhésion des Établissements"
        description="Instruction des demandes de raccordement des hôpitaux et cliniques à l'écosystème fédéré. Les hôpitaux conservent le contrôle exclusif de leurs données sources."
        actions={
          <div className="flex gap-2">
            <Button
              variant={filter === 'all' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('all')}
            >
              Tous ({applications.length})
            </Button>
            <Button
              variant={filter === 'pending' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('pending')}
            >
              À Réviser ({applications.filter((a) => a.status === 'human_review').length})
            </Button>
            <Button
              variant={filter === 'approved' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('approved')}
            >
              Approuvés ({applications.filter((a) => a.status === 'approved').length})
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Table of applications */}
        <div className="lg:col-span-7">
          <Card title="File des Demandes d'Adhésion" flush>
            <Table<HospitalApplication>
              caption="Liste des demandes d'adhésion des établissements hospitaliers"
              columns={[
                {
                  key: 'organization',
                  header: 'Établissement',
                  render: (app) => {
                    const org = governanceService.getOrganization(app.organizationId)
                    return (
                      <div>
                        <div className="font-medium text-slate-900">{org?.name ?? app.organizationId}</div>
                        <div className="text-xs text-slate-500">{org?.city ?? 'Tunisie'} • Réf: {app.id}</div>
                      </div>
                    )
                  },
                },
                {
                  key: 'status',
                  header: 'Statut',
                  render: (app) => {
                    if (app.status === 'human_review') {
                      return <Badge tone="warning" dot>Examen humain</Badge>
                    }
                    if (app.status === 'approved') {
                      return <Badge tone="success" dot>Approuvé</Badge>
                    }
                    return <Badge tone="neutral">{app.status}</Badge>
                  },
                },
                {
                  key: 'ai-assistance',
                  header: 'Assistance IA',
                  render: (app) => {
                    const aiStep = app.reviewSteps.find((s) => s.step === 'assisted_review')
                    if (!aiStep) return <span className="text-xs text-slate-400">N/A</span>
                    return (
                      <div className="flex items-center gap-1">
                        <DemoBadge>Consultative</DemoBadge>
                        {aiStep.findings.length > 0 && (
                          <span className="text-xs text-amber-700">({aiStep.findings.length} obs.)</span>
                        )}
                      </div>
                    )
                  },
                },
                {
                  key: 'action',
                  header: 'Action',
                  render: (app) => (
                    <Button
                      size="sm"
                      variant={selectedAppId === app.id ? 'primary' : 'ghost'}
                      onClick={() => setSelectedAppId(app.id)}
                    >
                      {selectedAppId === app.id ? 'Sélectionné' : 'Détails'}
                    </Button>
                  ),
                },
              ]}
              rows={filteredApps}
              getRowKey={(item) => item.id}
            />
          </Card>
        </div>

        {/* Inspection Panel */}
        <div className="lg:col-span-5">
          {selectedApp ? (
            <Card
              title={`Instruction : ${selectedOrg?.name ?? selectedApp.id}`}
              className="space-y-4"
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="text-xs text-slate-500">
                  Déposé le {new Date(selectedApp.submittedAt).toLocaleDateString('fr-TN')} par {governanceService.getPersonName(selectedApp.submittedById)}
                </span>
                {selectedApp.status === 'human_review' ? (
                  <Badge tone="warning" dot>Examen requis</Badge>
                ) : (
                  <Badge tone="success">Décision enregistrée</Badge>
                )}
              </div>

              {/* Review Steps */}
              {selectedApp.reviewSteps.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                    Étapes d'Instruction Préalable
                  </h4>
                  <div className="mt-2 space-y-2">
                    {selectedApp.reviewSteps.map((step, idx) => (
                      <div key={idx} className="rounded-md border border-slate-200 bg-slate-50 p-2.5 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-800">
                            {step.step === 'completeness_check' && '1. Contrôle de complétude documentaire'}
                            {step.step === 'assisted_review' && '2. Revue assistée par IA (Consultatif)'}
                            {step.step === 'human_review' && '3. Décision du réviseur de gouvernance'}
                          </span>
                          {step.advisory && <DemoBadge>IA Advisory</DemoBadge>}
                        </div>
                        {step.findings.length > 0 ? (
                          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-amber-900">
                            {step.findings.map((f, fi) => (
                              <li key={fi}>{f}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="mt-1 text-slate-500">
                            {step.status === 'pending'
                              ? 'En attente de conclusion par Pr Olfa Hamdi.'
                              : 'Aucune anomalie détectée.'}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Technical Questionnaire */}
              {selectedApp.technicalQuestionnaire && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                    Questionnaire Technique du Nœud Local
                  </h4>
                  <dl className="mt-2 grid grid-cols-2 gap-2 rounded-md bg-slate-50 p-3 text-xs">
                    <div>
                      <dt className="text-slate-500">Système DMI :</dt>
                      <dd className="font-medium text-slate-800">{selectedApp.technicalQuestionnaire.dmiSystem}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Base de données :</dt>
                      <dd className="font-medium text-slate-800">{selectedApp.technicalQuestionnaire.database}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Système hôte :</dt>
                      <dd className="font-medium text-slate-800">{selectedApp.technicalQuestionnaire.operatingSystem}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Réseau :</dt>
                      <dd className="font-medium text-slate-800 truncate" title={selectedApp.technicalQuestionnaire.network}>
                        {selectedApp.technicalQuestionnaire.network}
                      </dd>
                    </div>
                  </dl>
                </div>
              )}

              {/* Documents Checklist */}
              {selectedApp.documents.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                    Pièces Justificatives Fournies
                  </h4>
                  <ul className="mt-2 space-y-1.5 text-xs">
                    {selectedApp.documents.map((doc) => (
                      <li key={doc.id} className="flex items-center justify-between rounded border border-slate-200 px-2.5 py-1.5">
                        <span className="text-slate-800">{doc.title}</span>
                        {doc.status === 'received' ? (
                          <Badge tone="success">Reçu</Badge>
                        ) : (
                          <Badge tone="danger">Manquant</Badge>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Decision Section */}
              {selectedDecision ? (
                <div className="rounded-md border border-success-200 bg-success-50 p-3 text-xs">
                  <div className="font-semibold text-success-800">
                    Décision de Gouvernance : {selectedDecision.outcome === 'approved' ? 'Approuvée' : 'Rejetée'}
                  </div>
                  <p className="mt-1 text-success-700">« {selectedDecision.rationale} »</p>
                  <p className="mt-1 text-slate-500">
                    Validée par {governanceService.getPersonName(selectedDecision.decidedById)} le {new Date(selectedDecision.decidedAt).toLocaleDateString('fr-TN')}
                  </p>
                </div>
              ) : (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs">
                  <div className="font-semibold text-amber-900">En cours d'arbitrage par l'Autorité</div>
                  <p className="mt-1 text-amber-800">
                    Conformément aux invariants d'architecture, la décision finale appartient exclusivement aux réviseurs humains habilités (Pr Olfa Hamdi). L'avis de l'IA ne lie pas l'Autorité.
                  </p>
                </div>
              )}
            </Card>
          ) : (
            <Card>
              <div className="py-8 text-center text-xs text-slate-500">
                Sélectionnez un dossier d'adhésion pour en afficher les détails.
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
