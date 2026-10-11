import { useState } from 'react'
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
  type Tone,
} from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import {
  INSTALLATION_STEP_COUNT,
  nodeStatus,
  refreshNodeStatus,
  type HealthCheck,
  type IndicatorState,
  type NodeStatusReport,
} from '../services/nodeStatusService'
import type { OnboardingSnapshot, StepId } from '../types/onboarding'

interface NodeStatusViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make the refresh fail. */
  consumeSimulatedFailure: () => boolean
  onNavigate: (step: StepId) => void
}

const indicatorDisplay: Record<IndicatorState, { label: string; tone: Tone }> = {
  ok: { label: 'OK', tone: 'success' },
  warning: { label: 'À surveiller', tone: 'warning' },
  critical: { label: 'En échec', tone: 'danger' },
  unknown: { label: 'Inconnu', tone: 'neutral' },
}

const overallDisplay: Record<NodeStatusReport['node']['status'], { label: string; tone: Tone }> = {
  online: { label: 'En ligne', tone: 'success' },
  degraded: { label: 'Dégradé', tone: 'warning' },
  offline: { label: 'Hors ligne', tone: 'danger' },
}

const checkColumns: TableColumn<HealthCheck>[] = [
  { key: 'label', header: 'Contrôle', render: (c) => c.label, rowHeader: true },
  { key: 'detail', header: 'Résultat', render: (c) => c.detail },
  {
    key: 'state',
    header: 'État',
    align: 'right',
    render: (c) => <Badge tone={indicatorDisplay[c.state].tone}>{indicatorDisplay[c.state].label}</Badge>,
  },
]

export function NodeStatusView({ snapshot, consumeSimulatedFailure, onNavigate }: NodeStatusViewProps) {
  const status = nodeStatus(snapshot)

  const header = (
    <PageHeader
      eyebrow="Hospital Node · Étape 13"
      title="État du nœud"
      description="Connectivité, adaptateur DMI, version, contrôles de santé et synchronisation de votre Hospital Node."
      actions={<DemoBadge>Supervision simulée</DemoBadge>}
    />
  )

  if (status.kind === 'not_approved') {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Disponible après approbation"
            description="L'état du nœud s'affiche une fois l'adhésion approuvée et le Hospital Node installé."
            action={
              <Button variant="secondary" onClick={() => onNavigate('decision')}>
                Voir la décision
              </Button>
            }
          />
        </Card>
      </>
    )
  }

  if (status.kind === 'not_installed') {
    const declared = status.declaredSteps === INSTALLATION_STEP_COUNT
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun état reçu de votre nœud"
            description={
              declared
                ? "Vous avez déclaré l'installation terminée, mais aucun état n'a été reçu : dans cette démonstration, le portail ne reçoit pas l'état réel d'un nœud et ne le contacte jamais."
                : "Le Hospital Node n'est pas encore installé. Son état s'affichera ici une fois le nœud en service."
            }
            action={
              <Button variant="secondary" onClick={() => onNavigate('node-installation')}>
                {declared ? "Revoir le guide d'installation" : "Suivre le guide d'installation"}
              </Button>
            }
          />
        </Card>
      </>
    )
  }

  return (
    <>
      {header}
      <NodeDashboard report={status.report} snapshot={snapshot} consumeSimulatedFailure={consumeSimulatedFailure} />
    </>
  )
}

type Refresh = { kind: 'idle' } | { kind: 'refreshing' } | { kind: 'done'; checkedAt: string } | { kind: 'failed'; message: string }

function NodeDashboard({
  report,
  snapshot,
  consumeSimulatedFailure,
}: {
  report: NodeStatusReport
  snapshot: OnboardingSnapshot
  consumeSimulatedFailure: () => boolean
}) {
  const [refresh, setRefresh] = useState<Refresh>({ kind: 'idle' })
  const { node } = report
  const overall = overallDisplay[node.status]

  const check = async () => {
    setRefresh({ kind: 'refreshing' })
    try {
      const { checkedAt } = await refreshNodeStatus(snapshot, { simulateFailure: consumeSimulatedFailure() })
      setRefresh({ kind: 'done', checkedAt })
    } catch (error) {
      setRefresh({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
    }
  }

  return (
    <div className="space-y-6">
      <Alert tone="info" title="Supervision simulée">
        {node.simulated
          ? "Ce nœud est simulé par un scénario de démonstration : les états affichés sont fictifs et ne proviennent d'aucun nœud réel. "
          : 'Les états affichés proviennent des données de démonstration, pas d’un nœud réel. '}
        Le portail ne se connecte ni à votre nœud, ni à votre DMI : seul l'adaptateur DMI local au nœud le fait, et
        aucune donnée clinique ne transite par cette page.
      </Alert>

      {refresh.kind === 'failed' && (
        <Alert tone="danger" title="Actualisation impossible">
          {refresh.message} Le dernier état connu reste affiché.
        </Alert>
      )}

      <Card
        title={`Nœud ${node.id}`}
        actions={
          <Badge tone={overall.tone} dot>
            {overall.label}
          </Badge>
        }
        footer={
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-slate-500">
              {refresh.kind === 'done'
                ? `État vérifié le ${formatDateTime(refresh.checkedAt)} : aucun changement.`
                : 'Dernier état reçu affiché.'}
            </span>
            <Button size="sm" variant="secondary" loading={refresh.kind === 'refreshing'} onClick={() => void check()}>
              Actualiser
            </Button>
          </div>
        }
      >
        <ul className="hc-stagger grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {report.indicators.map((indicator) => (
            <li key={indicator.id} className="rounded-xl border border-line bg-surface-muted/50 p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-slate-500">{indicator.label}</p>
                <Badge tone={indicatorDisplay[indicator.state].tone}>{indicatorDisplay[indicator.state].label}</Badge>
              </div>
              <p className="mt-1 text-lg font-semibold text-slate-900">{indicator.value}</p>
              <p className="mt-1 text-sm text-slate-600">
                {indicator.detail}
                {indicator.at && ` ${formatDateTime(indicator.at)}`}
              </p>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Contrôles de santé" description="Résultats rapportés par le nœud lui-même." flush>
        <Table caption="Contrôles de santé du nœud" columns={checkColumns} rows={report.healthChecks} getRowKey={(c) => c.id} />
      </Card>
    </div>
  )
}
