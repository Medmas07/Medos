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
import type { ResearchAccessRequest } from '../../types/governance'

export function ResearchRequestsView() {
  const requests = governanceService.getResearchAccessRequests()
  const [selectedReqId, setSelectedReqId] = useState<string>('rar-002')

  const selectedReq = requests.find((r) => r.id === selectedReqId)
  const decision = selectedReq ? governanceService.getDecision(selectedReq.decisionId) : undefined
  const submitter = selectedReq ? governanceService.getPerson(selectedReq.submittedById) : undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Éthique & Recherche Biomédicale"
        title="Demandes d'Accès Projets de Recherche"
        description="Autorisation des projets de recherche multicentriques sous le paradigme Compute-to-Data. Aucun export de données brutes vers l'extérieur."
      />

      <Alert tone="info" title="Paradigme Compute-to-Data">
        Les algorithmes de recherche sont acheminés et exécutés au sein de l'environnement sécurisé des nœuds hospitaliers. Seuls des résultats agrégés et anonymisés (k-anonymat strict) peuvent être exportés après audit.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <Card title="Demandes d'Accès aux Données de Recherche" flush>
            <Table<ResearchAccessRequest>
              caption="Demandes d'accès des projets de recherche sous gouvernance éthique"
              columns={[
                {
                  key: 'project',
                  header: 'Projet & Réf.',
                  render: (req) => (
                    <div>
                      <div className="font-medium text-slate-900">{req.projectId}</div>
                      <div className="text-xs text-slate-500">Demande: {req.id}</div>
                    </div>
                  ),
                },
                {
                  key: 'researcher',
                  header: 'Chercheur / Institution',
                  render: (req) => {
                    const person = governanceService.getPerson(req.submittedById)
                    const org = person?.role ? governanceService.getOrganization('org-research-lab') : undefined
                    return (
                      <div className="text-xs">
                        <div className="font-semibold text-slate-800">
                          {person ? `${person.title ?? ''} ${person.firstName} ${person.lastName}` : req.submittedById}
                        </div>
                        <div className="text-slate-500">{org?.shortName ?? 'Laboratoire'}</div>
                      </div>
                    )
                  },
                },
                {
                  key: 'mode',
                  header: 'Mode d’Exécution',
                  render: () => (
                    <div className="flex items-center gap-1">
                      <Badge tone="info">Compute-to-Data</Badge>
                    </div>
                  ),
                },
                {
                  key: 'status',
                  header: 'Statut',
                  render: (req) => {
                    if (req.status === 'under_review') return <Badge tone="warning" dot>En examen</Badge>
                    if (req.status === 'approved') return <Badge tone="success" dot>Approuvé</Badge>
                    return <Badge tone="danger" dot>Rejeté</Badge>
                  },
                },
                {
                  key: 'action',
                  header: 'Action',
                  render: (req) => (
                    <Button
                      size="sm"
                      variant={selectedReqId === req.id ? 'primary' : 'ghost'}
                      onClick={() => setSelectedReqId(req.id)}
                    >
                      {selectedReqId === req.id ? 'Actif' : 'Examiner'}
                    </Button>
                  ),
                },
              ]}
              rows={requests}
              getRowKey={(item) => item.id}
            />
          </Card>
        </div>

        <div className="lg:col-span-5">
          {selectedReq ? (
            <Card title={`Dossier Éthique : ${selectedReq.projectId}`} className="space-y-4">
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Demandeur :</span>
                  <span className="font-medium text-slate-800">
                    {submitter ? `${submitter.title ?? ''} ${submitter.firstName} ${submitter.lastName}` : selectedReq.submittedById}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Soumis le :</span>
                  <span className="text-slate-800">
                    {new Date(selectedReq.submittedAt).toLocaleDateString('fr-TN')}
                  </span>
                </div>

                <div className="rounded bg-slate-50 p-2.5">
                  <div className="font-semibold text-slate-700">Contraintes Éthiques et Sécurité :</div>
                  <ul className="mt-1.5 list-disc space-y-1 pl-4 text-slate-600">
                    <li>Exécution confinée dans le sandbox du Nœud Hospitalier.</li>
                    <li>Interdiction absolue d'export des données individuelles brutes.</li>
                    <li>Agrégation minimale k &ge; 10 individus par cellule de résultat.</li>
                  </ul>
                </div>
              </div>

              {decision ? (
                <div className="rounded-md border border-success-200 bg-success-50 p-3 text-xs text-success-800">
                  <div className="font-semibold">Décision de l'Autorité : Approuvée</div>
                  <p className="mt-1">« {decision.rationale} »</p>
                  {decision.conditions.length > 0 && (
                    <div className="mt-2">
                      <span className="font-medium">Conditions fixées :</span>
                      <ul className="mt-1 list-disc pl-4">
                        {decision.conditions.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <p className="mt-2 text-slate-500">
                    Valide jusqu'au : {decision.validUntil ? new Date(decision.validUntil).toLocaleDateString('fr-TN') : 'Indéterminé'}
                  </p>
                </div>
              ) : (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                  <div className="flex items-center justify-between font-semibold">
                    <span>En cours d'examen par le comité éthique</span>
                    <DemoBadge>D1 Shell</DemoBadge>
                  </div>
                  <p className="mt-1 text-amber-800">
                    L'Autorité évalue le code algorithmique pour s'assurer qu'aucun modèle prédictif ou requête ne puisse réidentifier les patients.
                  </p>
                </div>
              )}
            </Card>
          ) : (
            <Card>
              <div className="py-8 text-center text-xs text-slate-500">
                Sélectionnez un projet de recherche pour afficher les détails.
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
