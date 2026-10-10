import { Alert, Badge, Card, DemoBadge, PageHeader, Table } from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import type { GovernanceAuditEvent } from '../../types/governance'

interface OverviewViewProps {
  onNavigate: (view: string) => void
}

export function OverviewView({ onNavigate }: OverviewViewProps) {
  const applications = governanceService.getHospitalApplications()
  const syncs = governanceService.getSynchronizationRequests()
  const research = governanceService.getResearchAccessRequests()
  const proofs = governanceService.getLedgerProofs()
  const auditEvents = governanceService.getAuditEvents().slice(0, 5)

  const pendingApps = applications.filter((a) => a.status === 'human_review' || a.status === 'pending').length
  const pendingSyncs = syncs.filter((s) => s.status === 'pending').length
  const underReviewResearch = research.filter((r) => r.status === 'under_review').length

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Tableau de bord — Autorité de Gouvernance"
        title="Vue d'Ensemble de l'Écosystème Fédéré"
        description="Supervision des demandes d'adhésion hospitalières, des flux de synchronisation inter-établissements et des preuves d'audit immuables."
      />

      <Alert tone="info" title="Invariants d'architecture">
        Les données médicales demeurent hébergées exclusivement au sein des Nœuds Hospitaliers respectifs. L'Autorité de Gouvernance applique les politiques et arbitre les accès sans jamais centraliser de base clinique.
      </Alert>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <button
          type="button"
          className="text-left w-full transition-transform hover:scale-[1.01] focus:outline-none"
          onClick={() => onNavigate('onboarding')}
        >
          <Card>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Adhésions Nœuds</span>
              {pendingApps > 0 ? (
                <Badge tone="warning" dot>{pendingApps} en attente</Badge>
              ) : (
                <Badge tone="success">À jour</Badge>
              )}
            </div>
            <div className="mt-3 text-3xl font-bold text-slate-900">{applications.length}</div>
            <p className="mt-1 text-xs text-slate-600">
              {pendingApps} dossier requiert une révision humaine (CH Cap Azur)
            </p>
          </Card>
        </button>

        <button
          type="button"
          className="text-left w-full transition-transform hover:scale-[1.01] focus:outline-none"
          onClick={() => onNavigate('synchronizations')}
        >
          <Card>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Synchronisations</span>
              {pendingSyncs > 0 ? (
                <Badge tone="warning" dot>{pendingSyncs} à valider</Badge>
              ) : (
                <Badge tone="neutral">0 en attente</Badge>
              )}
            </div>
            <div className="mt-3 text-3xl font-bold text-slate-900">{syncs.length}</div>
            <p className="mt-1 text-xs text-slate-600">
              Continuité des soins & autorisations de patients
            </p>
          </Card>
        </button>

        <button
          type="button"
          className="text-left w-full transition-transform hover:scale-[1.01] focus:outline-none"
          onClick={() => onNavigate('research')}
        >
          <Card>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Accès Recherche</span>
              {underReviewResearch > 0 ? (
                <Badge tone="info" dot>{underReviewResearch} en examen</Badge>
              ) : (
                <Badge tone="neutral">0 en cours</Badge>
              )}
            </div>
            <div className="mt-3 text-3xl font-bold text-slate-900">{research.length}</div>
            <p className="mt-1 text-xs text-slate-600">
              Projets biomédicaux en mode Compute-to-Data
            </p>
          </Card>
        </button>

        <button
          type="button"
          className="text-left w-full transition-transform hover:scale-[1.01] focus:outline-none"
          onClick={() => onNavigate('audit')}
        >
          <Card>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Preuves Registre</span>
              <DemoBadge>Simulées</DemoBadge>
            </div>
            <div className="mt-3 text-3xl font-bold text-slate-900">{proofs.length}</div>
            <p className="mt-1 text-xs text-slate-600">
              Preuves d'ancrage cryptographiques (SHA-256)
            </p>
          </Card>
        </button>
      </div>

      {/* Audit events feed */}
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
    </div>
  )
}
