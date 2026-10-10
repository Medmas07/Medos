import { useState, useSyncExternalStore } from 'react'
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
import { reviewStore } from '../../services/reviewStore'
import type { ResearchAccessRequest } from '../../types/governance'
import { ResearchReviewForm } from '../review/ResearchReviewForm'

/** The reviewer signed in to this demo portal (fictional, HC-005). */
const REVIEWER_ID = 'usr-olfa'

const formatDate = (iso: string) => new Date(iso).toLocaleDateString('fr-TN')

export function ResearchRequestsView() {
  // Re-render when a simulated decision is recorded or the demo is reset (HC-078).
  const reviewState = useSyncExternalStore(reviewStore.subscribe, reviewStore.getSnapshot)
  const simulatedCount = Object.keys(reviewState.researchAccessRequests).length
  const requests = governanceService.getResearchAccessRequests()
  const [selectedReqId, setSelectedReqId] = useState<string>('rar-002')

  const selectedReq = requests.find((r) => r.id === selectedReqId)
  const decision = selectedReq ? governanceService.getDecision(selectedReq.decisionId) : undefined
  const submitter = selectedReq ? governanceService.getPerson(selectedReq.submittedById) : undefined
  const project = selectedReq ? governanceService.getResearchProject(selectedReq.projectId) : undefined
  const researchOrg = submitter?.organizationId ? governanceService.getOrganization(submitter.organizationId) : undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Éthique & Recherche Biomédicale"
        title="Demandes d'Accès Projets de Recherche"
        description="Autorisation des projets de recherche multicentriques sous le paradigme Compute-to-Data. Aucun export de données brutes vers l'extérieur."
        actions={
          simulatedCount > 0 ? (
            <Button variant="ghost" size="sm" onClick={() => reviewStore.reset()}>
              Réinitialiser la démo
            </Button>
          ) : undefined
        }
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
                    const org = person?.organizationId ? governanceService.getOrganization(person.organizationId) : undefined
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
            <Card title={`Dossier Éthique : ${project?.title ?? selectedReq.projectId}`} className="space-y-4">
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Demandeur :</span>
                  <span className="text-right font-medium text-slate-800">
                    {governanceService.getPersonName(selectedReq.submittedById)}
                    {researchOrg && <span className="font-normal text-slate-500"> • {researchOrg.shortName}</span>}
                  </span>
                </div>
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Soumis le :</span>
                  <span className="text-slate-800">{formatDate(selectedReq.submittedAt)}</span>
                </div>

                {project ? (
                  <dl className="space-y-2 rounded bg-slate-50 p-2.5">
                    <div>
                      <dt className="font-semibold text-slate-700">Objectif</dt>
                      <dd className="text-slate-700">{project.summary}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-700">Population</dt>
                      <dd className="text-slate-700">{project.population}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-700">Variables demandées</dt>
                      <dd className="mt-1 flex flex-wrap gap-1">
                        {project.variables.map((v) => (
                          <Badge key={v} tone="neutral">{v}</Badge>
                        ))}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-700">Établissements participants</dt>
                      <dd className="text-slate-700">
                        {project.participatingOrganizationIds.map((id) => governanceService.getOrganization(id)?.shortName ?? id).join(', ')}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-700">Protocole</dt>
                      <dd className="text-slate-700">{project.protocolDocument?.title ?? 'Non fourni'}</dd>
                    </div>
                  </dl>
                ) : (
                  <Alert tone="danger" title="Projet introuvable">
                    La demande {selectedReq.id} ne correspond à aucun projet connu.
                  </Alert>
                )}

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
                <div
                  className={`rounded-md border p-3 text-xs ${
                    decision.outcome === 'approved'
                      ? 'border-success-200 bg-success-50 text-success-800'
                      : 'border-danger-200 bg-danger-50 text-danger-800'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">
                      Décision de l'Autorité : {decision.outcome === 'approved' ? 'Approuvée' : 'Rejetée'}
                    </span>
                    {decision.simulated && <DemoBadge>Simulée — non persistée</DemoBadge>}
                  </div>
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
                  {decision.outcome === 'approved' && (
                    <p className="mt-2 text-slate-500">
                      Valide jusqu'au : {decision.validUntil ? formatDate(decision.validUntil) : 'Indéterminé'}
                    </p>
                  )}
                  {decision.simulated && (
                    <p className="mt-2 text-slate-600">
                      Décidée par {governanceService.getPersonName(decision.decidedById)} le {formatDate(decision.decidedAt)}. Enregistrée dans l'état local du portail uniquement : l'API de recherche du Nœud de Gouvernance (HC-133) est planifiée, et ni le service de recherche ni les nœuds hospitaliers n'en sont informés.
                    </p>
                  )}
                </div>
              ) : selectedReq.status === 'under_review' ? (
                <ResearchReviewForm
                  key={selectedReq.id}
                  context={{
                    request: selectedReq,
                    project,
                    organization: (id) => governanceService.getOrganization(id),
                  }}
                  reviewer={governanceService.getPerson(REVIEWER_ID)}
                  reviewerName={governanceService.getPersonName(REVIEWER_ID)}
                />
              ) : (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                  Aucune décision n'est associée à cette demande.
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
