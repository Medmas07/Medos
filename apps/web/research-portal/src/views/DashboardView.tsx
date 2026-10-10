import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  Table,
  type TableColumn,
} from '@hackcure/design-system'
import {
  authorizationDisplay,
  formatDate,
  formatDateTime,
  jobStatusDisplay,
  lifecycleStepLabels,
  nextActionDisplay,
  priorityDisplay,
  stepReasonLabels,
  stepStateTone,
} from '../presentation'
import {
  deriveDashboard,
  type AuthorizationStatus,
  type LifecycleStep,
  type ProjectProgress,
} from '../services/dashboard'
import type { ComputeJob, PageId, ResearchSnapshot } from '../types/research'

interface DashboardViewProps {
  snapshot: ResearchSnapshot
  onNavigate: (page: PageId) => void
}

const markerTones = {
  neutral: 'bg-slate-300',
  info: 'bg-info-600',
  success: 'bg-success-600',
  warning: 'bg-warning-600',
  danger: 'bg-danger-600',
  demo: 'bg-demo-600',
} as const

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card>
      <p className="text-slate-600">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </Card>
  )
}

function stepDetail(step: LifecycleStep): string {
  if (step.reason) return stepReasonLabels[step.reason]
  if (step.at) return formatDate(step.at)
  if (step.state === 'current') return 'En cours'
  return 'À venir'
}

function ProjectLifecycle({ steps }: { steps: LifecycleStep[] }) {
  return (
    <ol aria-label="Étapes du projet" className="grid gap-3 sm:grid-cols-5">
      {steps.map((step) => (
        <li key={step.id} aria-current={step.state === 'current' ? 'step' : undefined} className="flex gap-2 sm:block">
          <span
            aria-hidden="true"
            className={`mt-1.5 block h-1.5 w-6 shrink-0 rounded-full sm:mt-0 sm:mb-2 sm:w-full ${markerTones[stepStateTone[step.state]]}`}
          />
          <div>
            <p className={`text-xs ${step.state === 'upcoming' ? 'text-slate-500' : 'font-medium text-slate-900'}`}>
              {lifecycleStepLabels[step.id]}
            </p>
            <p className="text-xs text-slate-500">{stepDetail(step)}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}

function ProjectCard({ progress, onNavigate }: { progress: ProjectProgress; onNavigate: (page: PageId) => void }) {
  const { summary, steps, next } = progress
  const action = nextActionDisplay[next.kind]
  const priority = priorityDisplay[next.priority]
  return (
    <Card
      title={summary.project.title}
      description={`${summary.project.id} · ${
        summary.participatingOrganizations.map((o) => o.shortName).join(', ') || 'aucun établissement'
      }`}
      actions={<Badge tone={priority.tone}>{priority.label}</Badge>}
    >
      <ProjectLifecycle steps={steps} />
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
        <div className="min-w-0">
          <p className="font-medium text-slate-900">{action.title}</p>
          <p className="text-slate-600">{action.description}</p>
        </div>
        <Button variant="secondary" onClick={() => onNavigate(next.page)}>
          {action.cta}
        </Button>
      </div>
    </Card>
  )
}

/** Researcher dashboard (HC-091): progress of each project through the governed Compute-to-Data workflow. */
export function DashboardView({ snapshot, onNavigate }: DashboardViewProps) {
  const dashboard = deriveDashboard(snapshot)
  const { metrics, authorizations } = dashboard

  const header = (
    <PageHeader
      eyebrow="Projets et demandes · HC-091"
      title="Tableau de bord"
      description={`Avancement des projets de ${snapshot.organization.name}, au ${formatDate(snapshot.asOf)}.`}
      actions={<Button onClick={() => onNavigate('new-project')}>Nouveau projet</Button>}
    />
  )

  if (dashboard.projects.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="Le tableau de bord suivra vos projets de la demande d'accès aux résultats contrôlés."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  const nextExpiry = authorizations
    .filter((a) => a.state !== 'expired' && a.summary.decision?.validUntil)
    .map((a) => a.summary.decision!.validUntil!)
    .sort()[0]
  const alerts = authorizations.filter((a) => a.state !== 'valid')
  const organizationName = (job: ComputeJob, id: string) =>
    snapshot.projects
      .find((s) => s.project.id === job.projectId)
      ?.participatingOrganizations.find((o) => o.id === id)?.shortName ?? id

  const authorizationColumns: TableColumn<AuthorizationStatus>[] = [
    {
      key: 'project',
      header: 'Projet',
      rowHeader: true,
      render: ({ summary }) => (
        <>
          <span className="font-medium text-slate-900">{summary.project.title}</span>
          <span className="block text-xs text-slate-500">
            {summary.decision!.id} · décidée le {formatDate(summary.decision!.decidedAt)}
          </span>
        </>
      ),
    },
    {
      key: 'conditions',
      header: 'Conditions',
      render: ({ summary }) =>
        summary.decision!.conditions.length > 0 ? (
          <ul className="list-disc space-y-0.5 pl-4 text-xs text-slate-600">
            {summary.decision!.conditions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        ) : (
          '—'
        ),
    },
    {
      key: 'validity',
      header: 'Validité',
      render: ({ summary, state, daysLeft }) => (
        <>
          <Badge tone={authorizationDisplay[state].tone}>{authorizationDisplay[state].label}</Badge>
          <span className="block text-xs text-slate-500">
            {summary.decision!.validUntil
              ? `${state === 'expired' ? 'depuis le' : "jusqu'au"} ${formatDate(summary.decision!.validUntil)}${
                  state === 'expired' ? '' : ` (${daysLeft} j)`
                }`
              : 'Sans échéance'}
          </span>
        </>
      ),
    },
  ]

  const jobColumns: TableColumn<ComputeJob>[] = [
    {
      key: 'job',
      header: 'Exécution',
      rowHeader: true,
      render: (job) => (
        <>
          <span className="font-medium text-slate-900">{job.id}</span>
          <span className="block text-xs text-slate-500">
            {snapshot.projects.find((s) => s.project.id === job.projectId)?.project.title}
          </span>
        </>
      ),
    },
    {
      key: 'nodes',
      header: 'Hospital Nodes',
      render: (job) =>
        job.stages
          .filter((s) => s.stage === 'execution')
          .map((s) => organizationName(job, s.organizationId))
          .join(', ') || '—',
    },
    {
      key: 'status',
      header: 'Statut',
      render: (job) => (
        <>
          <Badge tone={jobStatusDisplay[job.status].tone}>{jobStatusDisplay[job.status].label}</Badge>
          <span className="block text-xs text-slate-500">soumise le {formatDateTime(job.submittedAt)}</span>
        </>
      ),
    },
    {
      key: 'result',
      header: 'Résultat contrôlé',
      render: (job) => {
        const result = snapshot.results.find((r) => r.id === job.controlledResultId)
        if (!result) return <span className="text-xs text-slate-500">Aucun</span>
        return (
          <>
            <span className="text-slate-900">{result.title}</span>
            <span className="block text-xs text-slate-500">
              Contrôle de divulgation {result.disclosureCheck === 'passed' ? 'réussi' : 'échoué'} · effectif
              minimal {result.minimumCellSize}
            </span>
          </>
        )
      },
    },
  ]

  return (
    <>
      {header}

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Projets"
          value={String(metrics.projects)}
          hint={`${metrics.requestsUnderReview} demande(s) en revue par la gouvernance`}
        />
        <Metric
          label="Autorisations valides"
          value={String(metrics.validAuthorizations)}
          hint={nextExpiry ? `Prochaine échéance le ${formatDate(nextExpiry)}` : 'Aucune autorisation en cours'}
        />
        <Metric
          label="Exécutions terminées"
          value={`${metrics.completedJobs} / ${metrics.jobs}`}
          hint="Exécutions Compute-to-Data simulées"
        />
        <Metric
          label="Résultats contrôlés"
          value={String(metrics.releasedResults)}
          hint="Agrégats ayant passé le contrôle de divulgation"
        />
      </div>

      {alerts.map(({ summary, state, daysLeft }) => (
        <Alert
          key={summary.project.id}
          tone="warning"
          title={state === 'expired' ? 'Autorisation expirée' : `Autorisation expirant dans ${daysLeft} jour(s)`}
          className="mb-6"
        >
          {summary.project.title} : sans nouvelle décision de l'Autorité de gouvernance, aucune exécution ne sera
          possible {state === 'expired' ? 'pour ce projet' : `après le ${formatDate(summary.decision!.validUntil!)}`}.
        </Alert>
      ))}

      <section aria-labelledby="projects-progress" className="mb-6">
        <h2 id="projects-progress" className="mb-3 text-base">
          Suivi des projets
        </h2>
        <div className="space-y-4">
          {dashboard.projects.map((progress) => (
            <ProjectCard key={progress.summary.project.id} progress={progress} onNavigate={onNavigate} />
          ))}
        </div>
      </section>

      <Card
        title="Autorisations de gouvernance"
        description="Décisions de l'Autorité de gouvernance et d'éthique, affichées seulement : ce portail ne peut pas en enregistrer."
        actions={<DemoBadge>Fictif</DemoBadge>}
        flush
        className="mb-6"
      >
        <Table
          caption="Autorisations de gouvernance des projets"
          columns={authorizationColumns}
          rows={authorizations}
          getRowKey={({ summary }) => summary.project.id}
          empty={<EmptyState title="Aucune autorisation" description="Aucune demande d'accès n'a encore été approuvée." />}
        />
      </Card>

      <Card
        title="Exécutions Compute-to-Data"
        description="Le code a été exécuté dans les Hospital Nodes ; seuls des résultats agrégés et contrôlés reviennent."
        actions={<DemoBadge>Simulées</DemoBadge>}
        flush
      >
        <Table
          caption="Exécutions Compute-to-Data du chercheur"
          columns={jobColumns}
          rows={dashboard.jobs}
          getRowKey={(job) => job.id}
          empty={<EmptyState title="Aucune exécution" description="Les exécutions apparaîtront ici une fois un projet autorisé." />}
        />
      </Card>
    </>
  )
}
