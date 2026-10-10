import { useId, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  Table,
  TextField,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import type { HospitalApplication } from '../../types/governance'

export function HospitalOnboardingView() {
  const searchInputId = useId()
  const applications = governanceService.getHospitalApplications()
  const [filter, setFilter] = useState<'pending' | 'all' | 'approved'>('pending')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedAppId, setSelectedAppId] = useState<string>('app-hospital-c')

  const pendingApps = applications.filter(
    (app) => app.status === 'human_review' || app.status === 'pending'
  )
  const approvedApps = applications.filter((app) => app.status === 'approved')

  // Calculate pending queue metrics
  const missingDocsCount = pendingApps.reduce(
    (acc, app) => acc + app.documents.filter((d) => d.status === 'missing').length,
    0
  )
  const advisoryFindingsCount = pendingApps.reduce((acc, app) => {
    const aiStep = app.reviewSteps.find((s) => s.step === 'assisted_review')
    return acc + (aiStep?.findings.length ?? 0)
  }, 0)

  const filteredApps = applications.filter((app) => {
    // Status filter
    if (filter === 'pending' && app.status !== 'human_review' && app.status !== 'pending') {
      return false
    }
    if (filter === 'approved' && app.status !== 'approved') {
      return false
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim()
      const org = governanceService.getOrganization(app.organizationId)
      const matchesOrg = org?.name.toLowerCase().includes(q) || org?.city.toLowerCase().includes(q)
      const matchesId = app.id.toLowerCase().includes(q)
      const matchesDmi = app.technicalQuestionnaire?.dmiSystem.toLowerCase().includes(q)
      if (!matchesOrg && !matchesId && !matchesDmi) {
        return false
      }
    }

    return true
  })

  const selectedApp = applications.find((a) => a.id === selectedAppId)
  const selectedOrg = selectedApp ? governanceService.getOrganization(selectedApp.organizationId) : undefined
  const selectedDecision = selectedApp ? governanceService.getDecision(selectedApp.decisionId) : undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Gouvernance des Nœuds Hospitaliers (HC-072)"
        title="File des Demandes d'Adhésion Hospitalière"
        description="Instruction des demandes de raccordement des hôpitaux et cliniques à l'écosystème fédéré. Les hôpitaux conservent le contrôle exclusif de leurs données sources."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant={filter === 'pending' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('pending')}
            >
              À Réviser ({pendingApps.length})
            </Button>
            <Button
              variant={filter === 'all' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('all')}
            >
              Tous ({applications.length})
            </Button>
            <Button
              variant={filter === 'approved' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('approved')}
            >
              Approuvés ({approvedApps.length})
            </Button>
          </div>
        }
      />

      {/* KPI & Summary Banner */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-l-4 border-l-amber-500">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Dossiers en attente
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{pendingApps.length}</div>
          <p className="mt-1 text-xs text-amber-700 font-medium">
            Examen humain requis par l'Autorité
          </p>
        </Card>

        <Card className="border-l-4 border-l-rose-500">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Pièces manquantes
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{missingDocsCount}</div>
          <p className="mt-1 text-xs text-slate-600">
            Bloque la validation automatique
          </p>
        </Card>

        <Card className="border-l-4 border-l-sky-500">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Alertes IA Consultatives
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{advisoryFindingsCount}</div>
          <p className="mt-1 text-xs text-slate-600">
            Avis non-contraignant pour le réviseur
          </p>
        </Card>

        <Card className="border-l-4 border-l-emerald-500">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Réviseur habilité
          </div>
          <div className="mt-2 text-base font-bold text-slate-900">Pr Olfa Hamdi</div>
          <p className="mt-1 text-xs text-slate-600">
            Réf: usr-olfa • Décision humaine exclusive
          </p>
        </Card>
      </div>

      {/* Invariants & Safety Reminder */}
      <Alert tone="info" title="Principe d'Indépendance et Souveraineté Hospitalière">
        L'Autorité de Gouvernance instruit les dossiers d'adhésion technique et éthique. Elle n'héberge aucune donnée clinique locale et n'intervient pas dans les bases DMI des établissements. L'assistance algorithmique est strictement consultative.
      </Alert>

      {/* Search and Filters toolbar */}
      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="w-full sm:max-w-md">
            <TextField
              id={searchInputId}
              label="Rechercher un établissement ou une référence"
              placeholder="Ex: Cap Azur, Bizerte, MediDossier, app-hospital-c..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              hint="Filtre instantané sur le nom, la ville, le DMI ou la référence du dossier"
            />
          </div>
          {searchQuery && (
            <div className="flex items-center gap-2 pt-2 sm:pt-0">
              <Button size="sm" variant="secondary" onClick={() => setSearchQuery('')}>
                Effacer la recherche
              </Button>
            </div>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Table of applications */}
        <div className="lg:col-span-7">
          <Card
            title={
              filter === 'pending'
                ? "Demandes d'Adhésion en Attente de Revue"
                : filter === 'approved'
                  ? "Dossiers d'Adhésion Validés"
                  : "Toutes les Demandes d'Adhésion"
            }
            flush
          >
            <Table<HospitalApplication>
              caption="File des demandes d'adhésion hospitalière en attente ou traitées"
              columns={[
                {
                  key: 'organization',
                  header: 'Établissement & Ville',
                  render: (app) => {
                    const org = governanceService.getOrganization(app.organizationId)
                    return (
                      <div>
                        <div className="font-semibold text-slate-900">{org?.name ?? app.organizationId}</div>
                        <div className="text-xs text-slate-500">
                          {org?.city ?? 'Tunisie'} • Ref: <span className="font-mono text-slate-600">{app.id}</span>
                        </div>
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
                  key: 'documents',
                  header: 'Pièces',
                  render: (app) => {
                    if (app.documents.length === 0) {
                      return <span className="text-xs text-slate-400">Complété</span>
                    }
                    const missing = app.documents.filter((d) => d.status === 'missing').length
                    if (missing > 0) {
                      return (
                        <Badge tone="danger">
                          {missing} manquante{missing > 1 ? 's' : ''}
                        </Badge>
                      )
                    }
                    return (
                      <Badge tone="success">
                        {app.documents.length}/{app.documents.length} reçues
                      </Badge>
                    )
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
                          <span className="text-xs font-semibold text-amber-700">
                            ({aiStep.findings.length} obs.)
                          </span>
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
              empty={
                <div className="p-8">
                  <EmptyState
                    title="Aucun dossier trouvé"
                    description={
                      searchQuery
                        ? `Aucun établissement ne correspond à la recherche "${searchQuery}".`
                        : "Aucune demande d'adhésion ne correspond au filtre sélectionné."
                    }
                    action={
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setFilter('all')
                          setSearchQuery('')
                        }}
                      >
                        Réinitialiser les filtres
                      </Button>
                    }
                  />
                </div>
              }
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

              {/* Agreements */}
              {selectedApp.agreements.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                    Engagements Juridiques et Éthiques
                  </h4>
                  <ul className="mt-2 space-y-1 text-xs">
                    {selectedApp.agreements.map((agr) => (
                      <li key={agr.code} className="flex items-center justify-between rounded bg-slate-50 px-2.5 py-1">
                        <span className="text-slate-700">{agr.title}</span>
                        <Badge tone="success">Signé</Badge>
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
