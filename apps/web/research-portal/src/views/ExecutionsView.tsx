import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  Timeline,
  type TimelineItem,
} from '@hackcure/design-system'
import { executionPhaseDisplay, formatDateTime, jobStatusDisplay, stageStatusLabels, stageStatusTone } from '../presentation'
import {
  executionPhases,
  listExecutions,
  replayFrames,
  statusOfStages,
  type Execution,
  type ExecutionPhase,
} from '../services/executions'
import { organizationsByIds } from '../services/researchService'
import type { ComputeJobStage, PageId, ResearchSnapshot } from '../types/research'

interface ExecutionsViewProps {
  snapshot: ResearchSnapshot
  onNavigate: (page: PageId) => void
}

/** Simulated duration of each replay frame in milliseconds. */
const REPLAY_FRAME_MS = 700

const organizationOf = (id: string) => organizationsByIds([id])[0]

function stageTitle(stage: ComputeJobStage): string {
  const org = organizationOf(stage.organizationId)
  switch (stage.stage) {
    case 'authorization_check':
      return 'Vérification de l’autorisation par le Governance Node'
    case 'execution':
      return `Exécution locale dans ${org?.shortName ?? stage.organizationId}${org?.node ? ` (${org.node.id})` : ''}`
    case 'aggregation':
      return 'Agrégation contrôlée des résultats des nœuds'
    case 'output_validation':
      return 'Contrôle de divulgation avant mise à disposition'
  }
}

function PhaseBadge({ state }: { state: ExecutionPhase['state'] }) {
  return <Badge tone={stageStatusTone[state]}>{stageStatusLabels[state]}</Badge>
}

const phaseBorder: Record<ExecutionPhase['state'], string> = {
  pending: 'border-slate-200 bg-white',
  running: 'border-info-600 bg-info-50',
  completed: 'border-success-600 bg-white',
  failed: 'border-danger-600 bg-danger-50',
}

/** The governed path, left to right on wide screens: code goes to the data, only aggregates come back. */
function Pipeline({ execution, stages }: { execution: Execution; stages: ComputeJobStage[] }) {
  const phases = executionPhases(execution.submittedAt, stages)
  const nodeStages = stages.filter((s) => s.stage === 'execution')
  return (
    <ol aria-label="Parcours de l'exécution" className="grid gap-3 lg:grid-cols-5">
      {phases.map((phase, index) => {
        const display = executionPhaseDisplay[phase.id]
        return (
          <li
            key={phase.id}
            aria-current={phase.state === 'running' ? 'step' : undefined}
            className={`flex min-w-0 flex-col gap-2 rounded-lg border-2 p-3 ${phaseBorder[phase.state]}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-medium text-slate-500">Étape {index + 1}</span>
              <PhaseBadge state={phase.state} />
            </div>
            <p className="font-semibold text-slate-900">{display.title}</p>
            <p className="text-xs text-slate-600">
              {phase.id === 'authorization' && execution.decisionId
                ? `${display.description} Décision ${execution.decisionId}.`
                : display.description}
            </p>
            {phase.id === 'execution' && (
              <ul aria-label="Hospital Nodes" className="space-y-2">
                {nodeStages.map((s) => {
                  const org = organizationOf(s.organizationId)
                  return (
                    <li key={s.id} className="rounded-md border border-slate-200 bg-white p-2 text-xs">
                      <div className="flex flex-wrap items-center justify-between gap-1">
                        <span className="font-medium text-slate-800">{org?.shortName ?? s.organizationId}</span>
                        <PhaseBadge state={s.status} />
                      </div>
                      {org?.node && <code className="text-slate-500">{org.node.id}</code>}
                      <p className="text-slate-500">Les données restent dans le nœud.</p>
                    </li>
                  )
                })}
                {nodeStages.length === 0 && <li className="text-xs text-slate-500">Aucun Hospital Node.</li>}
              </ul>
            )}
            {phase.at && phase.state !== 'pending' && (
              <time dateTime={phase.at} className="mt-auto text-xs text-slate-500">
                {formatDateTime(phase.at)}
              </time>
            )}
          </li>
        )
      })}
    </ol>
  )
}

function StageTimeline({ stages }: { stages: ComputeJobStage[] }) {
  const items: TimelineItem[] = stages.map((s) => ({
    id: s.id,
    title: stageTitle(s),
    timestamp: s.completedAt ? formatDateTime(s.completedAt) : stageStatusLabels[s.status],
    dateTime: s.completedAt,
    meta: organizationOf(s.organizationId)?.name,
    tone: stageStatusTone[s.status],
    current: s.status === 'running',
  }))
  return <Timeline label="Étapes détaillées" items={items} />
}

function ExecutionOutcome({ execution, onNavigate }: { execution: Execution; onNavigate: (page: PageId) => void }) {
  if (execution.status === 'failed') {
    return (
      <Alert tone="danger" title="Exécution échouée">
        {execution.error ?? "Une étape a échoué. Aucun résultat, même partiel, n'est publié."}
      </Alert>
    )
  }
  if (execution.status !== 'completed') {
    return (
      <Alert tone="info" title="Exécution en cours">
        Le résultat ne sera disponible qu'après l'agrégation et le contrôle de divulgation.
      </Alert>
    )
  }
  if (execution.resultId) {
    return (
      <Alert
        tone="success"
        title={`Résultat contrôlé ${execution.resultId} publié`}
        actions={
          <Button size="sm" variant="secondary" onClick={() => onNavigate('results')}>
            Voir les résultats
          </Button>
        }
      >
        Seul un tableau agrégé ayant passé le contrôle de divulgation revient au chercheur
        {execution.origin === 'session' ? ' (résultat de démonstration du notebook fictif, non recalculé)' : ''}.
      </Alert>
    )
  }
  return (
    <Alert tone="demo" title="Aucun agrégat publié">
      {execution.output === 'no_release'
        ? "Le code n'appelle pas ctd.release : rien n'a quitté les Hospital Nodes."
        : "Le code modifié ou nouveau n'est pas interprété dans cette démonstration : les étapes sont simulées, mais aucun résultat n'est calculé."}
    </Alert>
  )
}

/** Compute-to-Data execution visualization (HC-100): fixture jobs and workspace runs, MOCKED replay. */
export function ExecutionsView({ snapshot, onNavigate }: ExecutionsViewProps) {
  const executions = listExecutions(snapshot)
  const [selectedId, setSelectedId] = useState(() => executions[0]?.id ?? '')
  const [replay, setReplay] = useState<{ executionId: string; frame: number } | null>(null)

  const execution = executions.find((e) => e.id === selectedId) ?? executions[0]
  const frames = replay && execution && replay.executionId === execution.id ? replayFrames(execution.stages) : null
  const replaying = frames !== null && replay !== null && replay.frame < frames.length - 1

  useEffect(() => {
    if (!replaying) return
    const timer = setTimeout(
      () => setReplay((r) => (r ? { ...r, frame: r.frame + 1 } : r)),
      REPLAY_FRAME_MS,
    )
    return () => clearTimeout(timer)
  }, [replaying, replay])

  const header = (
    <PageHeader
      eyebrow="Compute-to-Data · HC-100"
      title="Exécutions"
      description="Suivez chaque analyse : soumise, autorisée par le Governance Node, exécutée localement dans chaque Hospital Node, agrégée, puis contrôlée avant toute sortie."
      actions={<DemoBadge>Exécutions simulées</DemoBadge>}
    />
  )

  if (snapshot.projects.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="Les exécutions apparaissent une fois un projet autorisé par l'Autorité de gouvernance."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  if (snapshot.pages.find((p) => p.id === 'execution')?.status === 'locked') {
    return (
      <>
        {header}
        <Alert
          tone="neutral"
          title="Exécutions verrouillées"
          actions={
            <Button variant="secondary" size="sm" onClick={() => onNavigate('request-status')}>
              Suivre les demandes
            </Button>
          }
        >
          Aucun de vos projets ne détient une autorisation de gouvernance valide : aucune exécution n'est possible.
        </Alert>
      </>
    )
  }

  if (!execution) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune exécution"
            description="Exécutez une cellule de code dans l'espace de travail : son parcours Compute-to-Data apparaîtra ici."
            action={<Button onClick={() => onNavigate('workspace')}>Ouvrir l'espace de travail</Button>}
          />
        </Card>
      </>
    )
  }

  const stages = frames && replay ? frames[Math.min(replay.frame, frames.length - 1)] : execution.stages
  const status = frames ? statusOfStages(stages) : execution.status
  const statusDisplay = jobStatusDisplay[status]

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Visualisation simulée (D1)">
          Les exécutions sont celles des données fictives et celles lancées dans l'espace de travail pendant cette session
          (la dernière de chaque cellule). Rien n'est exécuté : aucun Research Service, Governance Node ni Hospital Node
          n'est contacté, et la relecture ne fait qu'animer les étapes enregistrées.
        </Alert>

        <Card title="Vos exécutions" description={`${executions.length} exécution(s), la plus récente d'abord.`}>
          <ul className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {executions.map((e) => {
              const display = jobStatusDisplay[e.status]
              const selected = e.id === execution.id
              return (
                <li key={e.id}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    onClick={() => {
                      setSelectedId(e.id)
                      setReplay(null)
                    }}
                    className={`w-full rounded-lg border p-3 text-left text-sm transition-colors focus:ring-2 focus:ring-brand-600/20 focus:outline-none ${
                      selected ? 'border-brand-600 bg-brand-50' : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <code className="text-xs break-all text-slate-700">{e.id}</code>
                      <Badge tone={display.tone}>{display.label}</Badge>
                    </div>
                    <p className="mt-1 font-medium text-slate-900">{e.summary.project.title}</p>
                    <p className="text-xs text-slate-500">
                      {e.origin === 'fixture' ? 'Exécution fictive' : `Espace de travail, exécution n° ${e.runNumber}`} ·{' '}
                      {formatDateTime(e.submittedAt)}
                    </p>
                  </button>
                </li>
              )
            })}
          </ul>
        </Card>

        <div className="min-w-0 space-y-6">
          <Card
            title={`Exécution ${execution.id}`}
            description={execution.summary.project.title}
            actions={
              <Button
                variant="secondary"
                onClick={() => setReplay({ executionId: execution.id, frame: 0 })}
                loading={replaying}
                disabled={replaying}
              >
                Rejouer
              </Button>
            }
          >
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-sm" aria-live="polite">
                <Badge tone={statusDisplay.tone}>{statusDisplay.label}</Badge>
                {frames && <Badge tone="demo">Relecture</Badge>}
              </div>
              <Pipeline execution={execution} stages={stages} />
              {!replaying && <ExecutionOutcome execution={execution} onNavigate={onNavigate} />}
            </div>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            <Card title="Étapes détaillées">
              <StageTimeline stages={stages} />
            </Card>
            <Card title="Provenance">
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-slate-500">Décision de gouvernance</dt>
                  <dd className="font-medium text-slate-900">{execution.decisionId ?? 'Inconnue'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Notebook</dt>
                  <dd className="text-slate-900">
                    {execution.notebookId ?? 'Inconnu'}
                    {execution.cellId && <span className="text-slate-500"> · cellule {execution.cellId}</span>}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Soumise le</dt>
                  <dd className="text-slate-900">{formatDateTime(execution.submittedAt)}</dd>
                </div>
                {execution.finishedAt && (
                  <div>
                    <dt className="text-slate-500">Terminée le</dt>
                    <dd className="text-slate-900">{formatDateTime(execution.finishedAt)}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-slate-500">Empreinte SHA-256 du code</dt>
                  <dd className="text-xs break-all text-slate-700">
                    {execution.algorithmSha256 ? (
                      <code>{execution.algorithmSha256}</code>
                    ) : (
                      'Non enregistrée pour cette exécution fictive.'
                    )}
                  </dd>
                </div>
              </dl>
              {execution.origin === 'session' && (
                <Button className="mt-4" size="sm" variant="ghost" onClick={() => onNavigate('workspace')}>
                  Ouvrir le notebook
                </Button>
              )}
            </Card>
          </div>
        </div>
      </div>
    </>
  )
}
