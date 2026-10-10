import { useMemo, useState } from 'react'
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
import {
  filterResearchRows,
  countResearchRows,
  researchListRows,
  RESEARCH_FILTER_LABELS,
  RESEARCH_FILTERS,
  type ResearchListFilter,
  type ResearchListRow,
} from '../../services/researchRequestList'

export function ResearchRequestsView() {
  const [filter, setFilter] = useState<ResearchListFilter>('all')
  const [selectedReqId, setSelectedReqId] = useState<string>('rar-002')

  // Use the browser clock at render time
  const now = useMemo(() => new Date(), [])

  const allRows = useMemo(() => {
    const rawRequests = governanceService.getResearchAccessRequests()
    return researchListRows(
      rawRequests,
      (projectId) => governanceService.getResearchProject(projectId),
      (decisionId) => governanceService.getDecision(decisionId),
      now,
    )
  }, [now])

  const counts = useMemo(() => countResearchRows(allRows), [allRows])
  const filteredRows = useMemo(() => filterResearchRows(allRows, filter), [allRows, filter])

  const selectedRow = allRows.find((r) => r.request.id === selectedReqId) ?? allRows[0]
  const selectedReq = selectedRow?.request
  const selectedProject = selectedRow?.project
  const decision = selectedReq ? governanceService.getDecision(selectedReq.decisionId) : undefined
  const submitter = selectedReq ? governanceService.getPerson(selectedReq.submittedById) : undefined

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Éthique & Recherche Biomédicale"
        title="Demandes d'Accès Projets de Recherche"
        description="Autorisation des projets de recherche multicentriques sous le paradigme Compute-to-Data. Aucun export de données brutes vers l'extérieur."
        actions={
          <div className="flex flex-wrap gap-2">
            {RESEARCH_FILTERS.map((f) => (
              <Button
                key={f}
                variant={filter === f ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilter(f)}
              >
                {RESEARCH_FILTER_LABELS[f]} ({counts[f]})
              </Button>
            ))}
          </div>
        }
      />

      <Alert tone="info" title="Paradigme Compute-to-Data & Protection des Données">
        Les algorithmes de recherche sont acheminés et exécutés au sein de l'environnement sécurisé des nœuds hospitaliers. Seuls des résultats agrégés et anonymisés (k-anonymat strict &ge; 10) peuvent être exportés après audit éthique.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Table of research requests */}
        <div className="lg:col-span-7">
          <Card title="File des Demandes d'Accès Recherche" flush>
            {filteredRows.length === 0 ? (
              <div className="p-8 text-center space-y-3">
                <p className="text-sm text-slate-500">
                  Aucune demande ne correspond au filtre « {RESEARCH_FILTER_LABELS[filter]} ».
                </p>
                <Button variant="secondary" size="sm" onClick={() => setFilter('all')}>
                  Afficher toutes les demandes ({counts.all})
                </Button>
              </div>
            ) : (
              <Table<ResearchListRow>
                caption="Demandes d'accès des projets de recherche sous gouvernance éthique"
                columns={[
                  {
                    key: 'project',
                    header: 'Projet & Réf.',
                    render: (row) => (
                      <div>
                        <div className="font-semibold text-slate-900 line-clamp-1">
                          {row.project?.title ?? row.request.projectId}
                        </div>
                        <div className="text-xs text-slate-500 font-mono">
                          {row.request.id} • {row.request.projectId}
                        </div>
                      </div>
                    ),
                  },
                  {
                    key: 'researcher',
                    header: 'Investigateur & Institution',
                    render: (row) => {
                      const person = governanceService.getPerson(row.request.submittedById)
                      const org = row.project?.organizationId
                        ? governanceService.getOrganization(row.project.organizationId)
                        : undefined
                      return (
                        <div className="text-xs">
                          <div className="font-medium text-slate-800">
                            {person ? `${person.title ? `${person.title} ` : ''}${person.firstName} ${person.lastName}` : row.request.submittedById}
                          </div>
                          <div className="text-slate-500">{org?.shortName ?? 'Laboratoire'}</div>
                        </div>
                      )
                    },
                  },
                  {
                    key: 'participating',
                    header: 'Nœuds Cibles',
                    render: (row) => {
                      const orgIds = row.project?.participatingOrganizationIds ?? []
                      const names = orgIds
                        .map((id) => governanceService.getOrganization(id)?.shortName ?? id)
                        .join(', ')
                      return (
                        <div className="text-xs">
                          <div className="font-medium text-slate-700">{orgIds.length} établissement{orgIds.length > 1 ? 's' : ''}</div>
                          <div className="text-slate-500 truncate max-w-[140px]" title={names}>
                            {names || 'Non précisé'}
                          </div>
                        </div>
                      )
                    },
                  },
                  {
                    key: 'mode',
                    header: 'Exécution',
                    render: () => (
                      <div className="flex items-center gap-1 text-xs">
                        <Badge tone="info">Compute-to-Data</Badge>
                      </div>
                    ),
                  },
                  {
                    key: 'status',
                    header: 'Statut',
                    render: (row) => {
                      if (row.status === 'under_review') return <Badge tone="warning" dot>En examen</Badge>
                      if (row.status === 'active') {
                        return (
                          <div className="text-xs">
                            <Badge tone="success" dot>Autorisée</Badge>
                            {row.validUntil && (
                              <div className="text-[10px] text-slate-400 mt-0.5">
                                jusqu'au {new Date(row.validUntil).toLocaleDateString('fr-TN')}
                              </div>
                            )}
                          </div>
                        )
                      }
                      if (row.status === 'expired') return <Badge tone="neutral" dot>Expirée</Badge>
                      return <Badge tone="danger" dot>Rejetée</Badge>
                    },
                  },
                  {
                    key: 'action',
                    header: 'Action',
                    render: (row) => (
                      <Button
                        size="sm"
                        variant={selectedReqId === row.request.id ? 'primary' : 'ghost'}
                        onClick={() => setSelectedReqId(row.request.id)}
                      >
                        {selectedReqId === row.request.id ? 'Actif' : 'Voir'}
                      </Button>
                    ),
                  },
                ]}
                rows={filteredRows}
                getRowKey={(item) => item.request.id}
              />
            )}
          </Card>
        </div>

        {/* Selected project details / preview panel */}
        <div className="lg:col-span-5">
          {selectedReq ? (
            <Card
              title={
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-900">
                    Dossier Éthique : {selectedReq.id}
                  </span>
                  <DemoBadge label="D1 — Fictif" />
                </div>
              }
              className="space-y-4"
            >
              <div>
                <h3 className="font-medium text-slate-900 text-sm">
                  {selectedProject?.title ?? selectedReq.projectId}
                </h3>
                {selectedProject?.summary && (
                  <p className="mt-1 text-xs text-slate-600 bg-slate-50 p-2.5 rounded-md">
                    {selectedProject.summary}
                  </p>
                )}
              </div>

              <div className="space-y-2 text-xs border-t border-slate-100 pt-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Investigateur Principal :</span>
                  <span className="font-medium text-slate-800">
                    {submitter ? `${submitter.title ? `${submitter.title} ` : ''}${submitter.firstName} ${submitter.lastName}` : selectedReq.submittedById}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Date de Soumission :</span>
                  <span className="text-slate-800 font-mono">
                    {new Date(selectedReq.submittedAt).toLocaleDateString('fr-TN')}
                  </span>
                </div>

                {selectedProject?.population && (
                  <div>
                    <span className="text-slate-500 font-medium">Population Cible :</span>
                    <p className="text-slate-700 mt-0.5">{selectedProject.population}</p>
                  </div>
                )}

                {selectedProject?.variables && selectedProject.variables.length > 0 && (
                  <div>
                    <span className="text-slate-500 font-medium">Variables requises :</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedProject.variables.map((v) => (
                        <Badge key={v} tone="neutral">{v}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {selectedProject?.protocolDocument && (
                  <div className="flex items-center justify-between bg-slate-50 p-2 rounded">
                    <span className="text-slate-600">Document Protocole :</span>
                    <span className="font-mono text-slate-800">{selectedProject.protocolDocument.title}</span>
                  </div>
                )}
              </div>

              {/* Ethical constraints summary */}
              <div className="rounded-lg bg-sky-50/80 border border-sky-100 p-2.5 text-xs">
                <div className="font-semibold text-sky-900">Garanties d'Architecture Compute-to-Data :</div>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sky-800 text-[11px]">
                  <li>Exécution dans l'environnement étanche du nœud hospitalier.</li>
                  <li>Interdiction d'export des données individuelles brutes.</li>
                  <li>Agrégation minimale k &ge; 10 individus par cellule.</li>
                </ul>
              </div>

              {/* Decision or pending status */}
              {decision ? (
                <div
                  className={`rounded-md border p-3 text-xs ${decision.outcome === 'approved'
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                    : 'border-rose-200 bg-rose-50 text-rose-800'
                    }`}
                >
                  <div className="font-semibold">
                    Décision de l'Autorité : {decision.outcome === 'approved' ? 'Approuvée' : 'Rejetée'}
                  </div>
                  <p className="mt-1">« {decision.rationale} »</p>
                  {decision.conditions.length > 0 && (
                    <div className="mt-2">
                      <span className="font-medium">Conditions fixées :</span>
                      <ul className="mt-0.5 list-disc pl-4 space-y-0.5">
                        {decision.conditions.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {decision.validUntil && (
                    <div className="mt-2 border-t border-emerald-200/60 pt-1 text-[11px] opacity-80">
                      Valide jusqu'au : {new Date(decision.validUntil).toLocaleDateString('fr-TN')}
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                  <div className="font-semibold">En cours d'examen par le comité éthique</div>
                  <p className="mt-1 text-amber-800">
                    L'Autorité vérifie la conformité éthique du protocole et garantit le respect du k-anonymat avant toute autorisation de calcul fédéré.
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
