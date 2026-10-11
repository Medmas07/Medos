import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  PageHeader,
  StatCard,
  StatGroup,
  Table,
} from '@hackcure/design-system'
import { auditTimeline } from '../../services/auditTimeline'
import { governanceService } from '../../services/governanceService'
import type { GovernanceAuditEvent, GovernanceDecision } from '../../types/governance'

interface OverviewViewProps {
  onNavigate: (view: string) => void
}

export function OverviewView({ onNavigate }: OverviewViewProps) {
  const [activeTab, setActiveTab] = useState<'all' | 'urgent' | 'nodes' | 'decisions'>('all')

  const metrics = governanceService.getDashboardMetrics()
  const applications = governanceService.getHospitalApplications()
  const syncs = governanceService.getSynchronizationRequests()
  const research = governanceService.getResearchAccessRequests()
  const nodes = governanceService.getFederatedHospitalNodes()
  const decisions = governanceService.getDecisions()
  // The six most recent events (HC-079 ordering); fixtures are stored oldest first.
  const auditEvents = auditTimeline(governanceService.getAuditEvents(), {
    decision: (id) => governanceService.getDecision(id),
    proofForEvent: (id) => governanceService.getProofForEvent(id),
  })
    .slice(0, 6)
    .map((entry) => entry.event)
  const notifications = governanceService.getReviewerNotifications('usr-olfa')

  const pendingApp = applications.find((a) => a.status === 'human_review')
  const pendingSync = syncs.find((s) => s.status === 'pending')
  const underReviewRes = research.find((r) => r.status === 'under_review')

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Autorité Indépendante de Gouvernance & d'Éthique"
        title="Tableau de Bord de Gouvernance Fédérée"
        description="Surveillance centrale des nœuds hospitaliers, arbitrage des flux de continuité des soins et traçabilité immuable des décisions."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={activeTab === 'all' ? 'primary' : 'secondary'}
              onClick={() => setActiveTab('all')}
            >
              Vue Complète
            </Button>
            <Button
              size="sm"
              variant={activeTab === 'urgent' ? 'primary' : 'secondary'}
              onClick={() => setActiveTab('urgent')}
            >
              Actions Requises ({metrics.pendingApplications + metrics.pendingSyncs + metrics.underReviewResearch})
            </Button>
            <Button
              size="sm"
              variant={activeTab === 'nodes' ? 'primary' : 'secondary'}
              onClick={() => setActiveTab('nodes')}
            >
              Nœuds Hospitaliers ({nodes.length})
            </Button>
            <Button
              size="sm"
              variant={activeTab === 'decisions' ? 'primary' : 'secondary'}
              onClick={() => setActiveTab('decisions')}
            >
              Décisions ({decisions.length})
            </Button>
          </div>
        }
      />

      {/* Authority Invariants Banner */}
      <Alert tone="info" title="Posture d'Indépendance et Invariants Fédérés">
        L'Autorité de Gouvernance est institutionnellement distincte des opérateurs techniques et des hôpitaux. Les données sources restent strictement sous souveraineté locale des établissements. Seules des autorisations d'échange et des empreintes cryptographiques de contrôle sont émises.
      </Alert>

      {/* Reviewer Notifications / Urgences */}
      {notifications.some((n) => !n.read) && (
        <Card title="Alertes & Dossiers Assignés — Pr Olfa Hamdi" actions={<DemoBadge>Réviseur Habilité</DemoBadge>}>
          <div className="space-y-2">
            {notifications.map((notif) => (
              <div
                key={notif.id}
                className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs"
              >
                <div className="flex items-center gap-3">
                  <span className="size-2 rounded-full bg-warning-600 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900">{notif.title}</span>
                    <p className="text-slate-600">{notif.body}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-400 text-[11px]">
                    {new Date(notif.createdAt).toLocaleDateString('fr-TN')}
                  </span>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      if (notif.relatedId?.startsWith('app-')) onNavigate('onboarding')
                      else if (notif.relatedId?.startsWith('sync-')) onNavigate('synchronizations')
                      else if (notif.relatedId?.startsWith('rar-')) onNavigate('research')
                    }}
                  >
                    Instruire
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* KPI Cards */}
      <StatGroup>
        <StatCard
          label="Adhésions Nœuds"
          value={metrics.totalApplications}
          hint={`${metrics.approvedHospitals} approuvés • ${metrics.pendingApplications} requiert révision humaine`}
          badge={
            metrics.pendingApplications > 0 ? (
              <Badge tone="warning" dot>{metrics.pendingApplications} en examen</Badge>
            ) : (
              <Badge tone="success">À jour</Badge>
            )
          }
          onClick={() => onNavigate('onboarding')}
        />
        <StatCard
          label="Flux Continuité"
          value={metrics.totalSyncs}
          hint={`${metrics.approvedSyncs} autorisés • ${metrics.rejectedSyncs} refusés`}
          badge={
            metrics.pendingSyncs > 0 ? (
              <Badge tone="warning" dot>{metrics.pendingSyncs} à arbitrer</Badge>
            ) : (
              <Badge tone="neutral">0 en attente</Badge>
            )
          }
          onClick={() => onNavigate('synchronizations')}
        />
        <StatCard
          label="Accès Recherche"
          value={metrics.totalResearchRequests}
          hint={`${metrics.approvedResearch} approuvés • Mode Compute-to-Data`}
          badge={
            metrics.underReviewResearch > 0 ? (
              <Badge tone="info" dot>{metrics.underReviewResearch} en examen</Badge>
            ) : (
              <Badge tone="neutral">0 en cours</Badge>
            )
          }
          onClick={() => onNavigate('research')}
        />
        <StatCard
          label="Preuves Registre"
          value={metrics.anchoredProofsCount}
          hint="100% vérifiées • Empreintes SHA-256 sans données cliniques"
          badge={<DemoBadge>Simulées D1</DemoBadge>}
          onClick={() => onNavigate('audit')}
        />
      </StatGroup>

      {/* Urgent Action Queues Panel (when tab is 'all' or 'urgent') */}
      {(activeTab === 'all' || activeTab === 'urgent') && (
        <Card
          title="Dossiers Prioritaires Nécessitant une Décision Humaine"
          actions={<Badge tone="warning" dot>3 Arbitrages en attente</Badge>}
        >
          <div className="hc-stagger grid grid-cols-1 gap-4 md:grid-cols-3">
            {pendingApp && (
              <div className="rounded-xl border border-warning-200 bg-warning-50/50 p-4 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-warning-800">Adhésion Établissement</span>
                  <Badge tone="warning">Examen requis</Badge>
                </div>
                <div className="font-bold text-slate-900">
                  {governanceService.getOrganizationName(pendingApp.organizationId)}
                </div>
                <p className="text-slate-600">
                  Dossier technique déposé par Mehdi Sassi. Attestation d'assurance manquante.
                </p>
                <div className="pt-2">
                  <Button size="sm" variant="primary" onClick={() => onNavigate('onboarding')}>
                    Examiner la candidature
                  </Button>
                </div>
              </div>
            )}

            {pendingSync && (
              <div className="rounded-xl border border-warning-200 bg-warning-50/50 p-4 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-warning-800">Synchronisation Soins</span>
                  <Badge tone="warning">En attente</Badge>
                </div>
                <div className="font-bold text-slate-900 truncate" title={pendingSync.purpose}>
                  {pendingSync.purpose}
                </div>
                <p className="text-slate-600">
                  HU Bab Ennour → HR Oued Zitoun pour Leïla Mansouri. Base : consentement actif.
                </p>
                <div className="pt-2">
                  <Button size="sm" variant="primary" onClick={() => onNavigate('synchronizations')}>
                    Arbitrer la demande
                  </Button>
                </div>
              </div>
            )}

            {underReviewRes && (
              <div className="rounded-xl border border-info-200 bg-info-50/50 p-4 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-info-800">Projet de Recherche</span>
                  <Badge tone="info">Comité éthique</Badge>
                </div>
                <div className="font-bold text-slate-900">
                  Projet {underReviewRes.projectId}
                </div>
                <p className="text-slate-600">
                  Déposé par Dr Aymen Rezgui. Exécution confinée Compute-to-Data à valider.
                </p>
                <div className="pt-2">
                  <Button size="sm" variant="primary" onClick={() => onNavigate('research')}>
                    Instruire l'accès
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Federated Nodes Grid (when tab is 'all' or 'nodes') */}
      {(activeTab === 'all' || activeTab === 'nodes') && (
        <Card
          title="État du Réseau des Nœuds Fédérés"
          actions={
            <div className="flex gap-2">
              <Badge tone="success" dot>{metrics.onlineNodesCount} en ligne</Badge>
              {metrics.degradedNodesCount > 0 && (
                <Badge tone="warning" dot>{metrics.degradedNodesCount} dégradé</Badge>
              )}
            </div>
          }
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {nodes.map((org) => {
              const isOnline = org.node?.status === 'online'
              const isDegraded = org.node?.status === 'degraded'
              return (
                <div
                  key={org.id}
                  className="rounded-xl border border-slate-200 bg-surface p-4 text-xs space-y-2 shadow-card"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900 truncate" title={org.name}>
                      {org.shortName}
                    </span>
                    {org.node ? (
                      <Badge tone={isOnline ? 'success' : isDegraded ? 'warning' : 'danger'} dot>
                        {org.node.status}
                      </Badge>
                    ) : (
                      <Badge tone="neutral">En attente</Badge>
                    )}
                  </div>
                  <div className="text-slate-500">{org.city} • {org.type === 'hospital' ? 'Centre Hospitalier' : 'Cabinet'}</div>
                  <div className="border-t border-slate-100 pt-2 space-y-1 text-[11px] text-slate-600">
                    <div className="flex justify-between">
                      <span>DMI local :</span>
                      <span className="font-medium text-slate-800">{org.node?.dmiState ?? 'Non raccordé'}</span>
                    </div>
                    {org.node?.lastSyncAt && (
                      <div className="flex justify-between">
                        <span>Dernière synchro :</span>
                        <span className="font-mono text-slate-700">
                          {new Date(org.node.lastSyncAt).toLocaleTimeString('fr-TN', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Decisions History (when tab is 'decisions') */}
      {activeTab === 'decisions' && (
        <Card title="Registre des Décisions d'Arbitrage Émises" flush>
          <Table<GovernanceDecision>
            caption="Décisions officielles de l'Autorité de Gouvernance"
            columns={[
              {
                key: 'id',
                header: 'Réf. Décision',
                render: (d) => <span className="font-mono text-xs font-semibold text-slate-900">{d.id}</span>,
              },
              {
                key: 'type',
                header: 'Type de Demande',
                render: (d) => <Badge tone="neutral">{d.subjectType}</Badge>,
              },
              {
                key: 'outcome',
                header: 'Arbitrage',
                render: (d) => (
                  <Badge tone={d.outcome === 'approved' ? 'success' : 'danger'} dot>
                    {d.outcome === 'approved' ? 'Approuvé' : 'Rejeté'}
                  </Badge>
                ),
              },
              {
                key: 'rationale',
                header: 'Motivation & Rationale',
                render: (d) => (
                  <div className="max-w-md text-xs text-slate-700">
                    <p>« {d.rationale} »</p>
                    {d.conditions.length > 0 && (
                      <span className="text-[11px] text-brand-700">({d.conditions.length} condition(s) stipulée(s))</span>
                    )}
                  </div>
                ),
              },
              {
                key: 'reviewer',
                header: 'Réviseur Habilité',
                render: (d) => (
                  <span className="text-xs text-slate-600">
                    {governanceService.getPersonName(d.decidedById)}
                  </span>
                ),
              },
              {
                key: 'date',
                header: 'Date',
                render: (d) => (
                  <span className="text-xs text-slate-500">
                    {new Date(d.decidedAt).toLocaleDateString('fr-TN')}
                  </span>
                ),
              },
            ]}
            rows={decisions}
            getRowKey={(item) => item.id}
          />
        </Card>
      )}

      {/* Recent Audit Events Stream (when tab is 'all') */}
      {activeTab === 'all' && (
        <Card title="Dernières Actions & Événements d'Audit de Gouvernance" flush>
          <Table<GovernanceAuditEvent>
            caption="Derniers événements d'audit enregistrés par la gouvernance"
            columns={[
              {
                key: 'timestamp',
                header: 'Horodatage',
                render: (evt) => (
                  <span className="font-mono text-xs text-slate-600">
                    {new Date(evt.at).toLocaleString('fr-TN', { dateStyle: 'short', timeStyle: 'short' })}
                  </span>
                ),
              },
              {
                key: 'action',
                header: 'Action',
                render: (evt) => (
                  <span className="font-medium text-slate-900">
                    {evt.action === 'decision_recorded' && 'Décision enregistrée'}
                    {evt.action === 'application_submitted' && 'Dossier d’adhésion déposé'}
                    {evt.action === 'request_received' && 'Demande reçue'}
                    {evt.action === 'proof_verified' && 'Preuve vérifiée'}
                  </span>
                ),
              },
              {
                key: 'subject',
                header: 'Objet & Référence',
                render: (evt) => (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-700">{evt.subjectId}</span>
                    <Badge tone="neutral">{evt.subjectType}</Badge>
                  </div>
                ),
              },
              {
                key: 'actor',
                header: 'Acteur',
                render: (evt) => (
                  <span className="text-xs text-slate-600">
                    {governanceService.getPersonName(evt.actorId)}
                  </span>
                ),
              },
              {
                key: 'proof',
                header: 'Preuve Registre',
                render: (evt) => {
                  const proof = governanceService.getProofForEvent(evt.id)
                  return proof ? (
                    <Badge tone="success" dot>Preuve ancrée ({proof.id})</Badge>
                  ) : (
                    <span className="text-xs text-slate-400">Non ancré</span>
                  )
                },
              },
            ]}
            rows={auditEvents}
            getRowKey={(item) => item.id}
          />
        </Card>
      )}
    </div>
  )
}
