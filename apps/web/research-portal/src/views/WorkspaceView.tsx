import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  Table,
  Timeline,
  type TimelineItem,
} from '@hackcure/design-system'
import {
  authorizationDisplay,
  cellCheckLabels,
  cellCheckTone,
  cellRunDisplay,
  formatDate,
  formatDateTime,
  stageStatusLabels,
  stageStatusTone,
  unavailableReasonDisplay,
} from '../presentation'
import { organizationsByIds } from '../services/researchService'
import {
  addCell,
  APPROVED_PACKAGES,
  isStale,
  notebookFor,
  recordCellRun,
  removeCell,
  runCell,
  updateCellSource,
  withNotebook,
  workspaceAccess,
  type WorkspaceContext,
} from '../services/workspace'
import type { CellRun, ComputeJobStage, Notebook, NotebookCell, PageId, ResearchSnapshot } from '../types/research'

interface WorkspaceViewProps {
  snapshot: ResearchSnapshot
  /** Whether the run being dispatched should fail in a Hospital Node (demo scenario). */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}

/** A run in progress: the cell running, its live stages, and the cells waiting after it. */
interface Progress {
  cellId: string
  stages: ComputeJobStage[]
  queued: string[]
}

const PLATFORM_ORGANIZATIONS = organizationsByIds(['org-governance', 'org-platform'])

function stageTitle(stage: ComputeJobStage, context: WorkspaceContext): string {
  switch (stage.stage) {
    case 'authorization_check':
      return 'Vérification de l’autorisation par le Governance Node'
    case 'execution': {
      const org = context.nodes.find((o) => o.id === stage.organizationId)
      return `Exécution locale dans ${org?.shortName ?? stage.organizationId}${org?.node ? ` (${org.node.id})` : ''}`
    }
    case 'aggregation':
      return 'Agrégation contrôlée des résultats des nœuds'
    case 'output_validation':
      return 'Contrôle de divulgation avant mise à disposition'
  }
}

function StageTimeline({ stages, context, label }: { stages: ComputeJobStage[]; context: WorkspaceContext; label: string }) {
  const items: TimelineItem[] = stages.map((s) => ({
    id: s.id,
    title: stageTitle(s, context),
    timestamp: s.completedAt ? formatDateTime(s.completedAt) : stageStatusLabels[s.status],
    dateTime: s.completedAt,
    meta: PLATFORM_ORGANIZATIONS.find((o) => o.id === s.organizationId)?.name,
    tone: stageStatusTone[s.status],
    current: s.status === 'running',
  }))
  return <Timeline label={label} items={items} />
}

function MarkdownPreview({ source }: { source: string }) {
  if (!source.trim()) return <p className="text-sm text-slate-400 italic">Cellule de texte vide.</p>
  return (
    <div className="space-y-2 text-sm text-slate-800">
      {source.split('\n').map((line, i) => {
        const heading = /^(#{1,3})\s+(.*)$/.exec(line)
        if (heading) return <p key={i} className="text-base font-semibold text-slate-900">{heading[2]}</p>
        return line.trim() ? <p key={i}>{line}</p> : null
      })}
    </div>
  )
}

function RunOutput({ run, context, stale }: { run: CellRun; context: WorkspaceContext; stale: boolean }) {
  const display = cellRunDisplay[run.status]
  const { output } = run
  return (
    <div className="space-y-4 border-t border-slate-200 pt-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <Badge tone={display.tone}>{display.label}</Badge>
        <span>
          Exécution simulée n° {run.number} · {formatDateTime(run.startedAt)}
        </span>
        {stale && <Badge tone="warning">Code modifié depuis</Badge>}
      </div>

      <ul aria-label="Contrôles avant envoi" className="flex flex-wrap gap-2">
        {run.checks.map((c) => (
          <li key={c.id}>
            <Badge tone={cellCheckTone[c.state]}>
              <span title={c.detail}>{cellCheckLabels[c.id]}</span>
            </Badge>
          </li>
        ))}
      </ul>

      {run.error && (
        <Alert tone={run.status === 'failed' ? 'danger' : 'warning'} title={run.status === 'failed' ? 'Exécution échouée' : 'Exécution refusée'}>
          {run.error}
        </Alert>
      )}

      {run.stages.length > 0 && <StageTimeline stages={run.stages} context={context} label={`Étapes de l'exécution n° ${run.number}`} />}

      {output.kind === 'aggregate' && (
        <div className="space-y-2">
          <Table
            caption={output.result.title}
            showCaption
            columns={output.columns.map((header, i) => ({
              key: String(i),
              header,
              render: (row: (string | number)[]) => row[i],
              align: i > 0 ? ('right' as const) : ('left' as const),
              rowHeader: i === 0,
            }))}
            rows={output.rows}
            getRowKey={(row) => String(row[0])}
          />
          <p className="text-xs text-slate-500">
            Résultat de démonstration {output.result.id} (données fictives, non recalculé) · effectif minimal{' '}
            {output.result.minimumCellSize} · contrôle de divulgation réussi. {output.result.provenance}
          </p>
        </div>
      )}
      {output.kind === 'no_release' && (
        <p className="text-sm text-slate-600">
          Aucune sortie : sans appel à <code>ctd.release</code>, rien ne quitte les Hospital Nodes.
        </p>
      )}
      {output.kind === 'not_simulated' && (
        <Alert tone="demo" title="Aucun agrégat calculé (D1)">
          Le code modifié ou nouveau n'est pas interprété dans cette démonstration : les étapes sont simulées, mais aucun
          résultat n'est calculé. Seul le code d'origine du notebook fictif renvoie son résultat de démonstration.
        </Alert>
      )}

      {run.algorithmSha256 && (
        <p className="text-xs break-all text-slate-500">
          Empreinte SHA-256 du code envoyé (provenance) : <code>{run.algorithmSha256}</code>
        </p>
      )}
    </div>
  )
}

interface CellViewProps {
  cell: NotebookCell
  index: number
  context: WorkspaceContext
  progress: Progress | null
  busy: boolean
  onChange: (source: string) => void
  onRun: () => void
  onRemove: () => void
}

function CellView({ cell, index, context, progress, busy, onChange, onRun, onRemove }: CellViewProps) {
  const [editing, setEditing] = useState(false)
  const running = progress?.cellId === cell.id
  const queued = progress?.queued.includes(cell.id) ?? false
  const label = cell.type === 'code' ? `Code [${index}]` : 'Texte'
  const live = running ? cellRunDisplay.running : queued ? cellRunDisplay.queued : null

  return (
    <li className="rounded-lg border border-slate-200 bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
          <span>{label}</span>
          {cell.type === 'code' && <span className="text-slate-400">Python (simulé)</span>}
          {live && <Badge tone={live.tone}>{live.label}</Badge>}
        </div>
        <div className="flex flex-wrap gap-2">
          {cell.type === 'code' ? (
            <Button size="sm" onClick={onRun} disabled={busy} loading={running} aria-label={`Exécuter la cellule ${label}`}>
              Exécuter
            </Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={() => setEditing((e) => !e)} disabled={busy}>
              {editing ? 'Terminer' : 'Modifier'}
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={onRemove} disabled={busy} aria-label={`Supprimer la cellule ${label}`}>
            Supprimer
          </Button>
        </div>
      </div>
      <div className="space-y-4 p-3">
        {cell.type === 'markdown' && !editing ? (
          <MarkdownPreview source={cell.source} />
        ) : (
          <textarea
            aria-label={`Source de la cellule ${label}`}
            value={cell.source}
            onChange={(e) => onChange(e.target.value)}
            readOnly={busy}
            spellCheck={false}
            rows={Math.max(3, cell.source.split('\n').length + 1)}
            className={`w-full resize-y rounded-xl border border-slate-300 bg-slate-50 p-3 text-sm text-slate-900 focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20 focus:outline-none ${
              cell.type === 'code' ? 'font-mono whitespace-pre' : ''
            }`}
          />
        )}
        {running && progress && (
          <StageTimeline stages={progress.stages} context={context} label="Étapes de l'exécution en cours" />
        )}
        {!running && cell.lastRun && <RunOutput run={cell.lastRun} context={context} stale={isStale(cell)} />}
      </div>
    </li>
  )
}

function AuthorizationContext({ context }: { context: WorkspaceContext }) {
  const { summary, decision, authorization } = context
  const criteria = summary.project.populationCriteria
  const display = authorizationDisplay[authorization.state]
  return (
    <Card title="Contexte d'autorisation" description="Chaque exécution est liée à cette décision et à son périmètre.">
      <dl className="space-y-4 text-sm">
        <div>
          <dt className="text-slate-500">Décision de gouvernance</dt>
          <dd className="space-y-1">
            <div className="font-medium text-slate-900">
              {decision.id} · demande {summary.request?.id}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={display.tone}>{display.label}</Badge>
              <span className="text-slate-600">
                {decision.validUntil
                  ? `jusqu'au ${formatDate(decision.validUntil)}${authorization.daysLeft !== null ? ` (${authorization.daysLeft} j)` : ''}`
                  : 'Sans échéance'}
              </span>
            </div>
          </dd>
        </div>
        {decision.conditions.length > 0 && (
          <div>
            <dt className="text-slate-500">Conditions</dt>
            <dd>
              <ul className="list-disc space-y-0.5 pl-4 text-slate-800">
                {decision.conditions.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </dd>
          </div>
        )}
        <div>
          <dt className="text-slate-500">Hospital Nodes d'exécution</dt>
          <dd>
            <ul className="space-y-1">
              {context.nodes.map((o) => (
                <li key={o.id} className="flex flex-wrap items-center gap-2 text-slate-800">
                  <span className="font-medium">{o.shortName}</span>
                  <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{o.node?.id}</code>
                  {(o.node?.status !== 'online' || o.node?.dmiState !== 'connected') && (
                    <Badge tone="warning">Nœud dégradé</Badge>
                  )}
                </li>
              ))}
              {context.withoutNode.map((o) => (
                <li key={o.id} className="text-slate-500">
                  {o.shortName} : aucun Hospital Node, aucune exécution possible.
                </li>
              ))}
            </ul>
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Population</dt>
          <dd className="text-slate-800">
            {criteria ? (
              <ul className="list-disc pl-4">
                {(criteria.ageMin !== undefined || criteria.ageMax !== undefined) && (
                  <li>
                    Âge : {criteria.ageMin ?? 0} à {criteria.ageMax ?? 130} ans
                  </li>
                )}
                {(criteria.encounterFrom || criteria.encounterTo) && (
                  <li>
                    Consultation entre {criteria.encounterFrom ?? '…'} et {criteria.encounterTo ?? '…'}
                  </li>
                )}
              </ul>
            ) : (
              <>
                {summary.project.population}
                <span className="block text-xs text-slate-500">Critères non structurés (projet fictif).</span>
              </>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Variables autorisées</dt>
          <dd className="flex flex-wrap gap-1.5">
            {context.variables.map((v) => (
              <code key={v.name} title={v.label} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
                {v.name}
              </code>
            ))}
            {context.unmatchedVariables.map((label) => (
              <span key={label} className="text-xs text-slate-500">
                {label} (hors catalogue)
              </span>
            ))}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Politique de sortie</dt>
          <dd className="text-slate-800">
            Tableau agrégé uniquement, effectif minimal de {context.minimumCellSize} par cellule, contrôle de divulgation
            obligatoire.
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Environnement (simulé)</dt>
          <dd className="space-y-1 text-slate-800">
            <div className="flex flex-wrap gap-1.5">
              {APPROVED_PACKAGES.map((p) => (
                <code key={p} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
                  {p}
                </code>
              ))}
            </div>
            <p className="text-xs text-slate-500">
              Python, paquets approuvés seulement ; <code>ctd</code> est l'API Compute-to-Data fictive, préchargée. Chaque
              cellule de code est envoyée comme une analyse complète : aucun état n'est partagé entre cellules.
            </p>
          </dd>
        </div>
      </dl>
    </Card>
  )
}

/** Colab-like research workspace (HC-099): notebook in session state, MOCKED Compute-to-Data runs. */
export function WorkspaceView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: WorkspaceViewProps) {
  const access = workspaceAccess(snapshot)
  const [selectedId, setSelectedId] = useState(() => access.contexts[0]?.summary.project.id ?? '')
  const [progress, setProgress] = useState<Progress | null>(null)
  // Runs resolve after the props have changed: always build on the latest snapshot.
  const snapshotRef = useRef(snapshot)
  useLayoutEffect(() => {
    snapshotRef.current = snapshot
  }, [snapshot])
  const abortRef = useRef<AbortController | null>(null)
  useEffect(() => () => abortRef.current?.abort(), [])

  const header = (
    <PageHeader
      eyebrow="Compute-to-Data · HC-099"
      title="Espace de travail"
      description="Écrivez l'analyse dans un notebook : le code est envoyé aux Hospital Nodes autorisés, seuls des résultats agrégés contrôlés reviennent."
      actions={<DemoBadge>Exécution simulée</DemoBadge>}
    />
  )

  if (snapshot.projects.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="L'espace de travail s'ouvre une fois un projet autorisé par l'Autorité de gouvernance."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  const context = access.contexts.find((c) => c.summary.project.id === selectedId) ?? access.contexts[0]
  if (!context) {
    return (
      <>
        {header}
        <Alert tone="neutral" title="Espace de travail verrouillé" className="mb-6">
          Aucun de vos projets ne détient une autorisation de gouvernance valide. Aucune exécution n'est possible : ni ce
          portail ni l'opérateur de la plateforme ne peuvent l'autoriser.
        </Alert>
        <Card
          title="Vos projets"
          actions={
            <Button variant="secondary" size="sm" onClick={() => onNavigate('request-status')}>
              Suivre les demandes
            </Button>
          }
        >
          <ul className="divide-y divide-slate-200">
            {access.unavailable.map(({ summary, reason }) => (
              <li key={summary.project.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="font-medium text-slate-900">{summary.project.title}</p>
                  <p className="text-xs text-slate-500">{summary.project.id}</p>
                </div>
                <Badge tone={unavailableReasonDisplay[reason].tone}>{unavailableReasonDisplay[reason].label}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </>
    )
  }

  const notebook = notebookFor(snapshot, context)
  const busy = progress !== null
  const save = (next: Notebook) => onUpdated(withNotebook(snapshotRef.current, next))
  const latestNotebook = () => notebookFor(snapshotRef.current, context)

  const run = async (cellIds: string[]) => {
    const controller = new AbortController()
    abortRef.current = controller
    for (let i = 0; i < cellIds.length; i++) {
      const cellId = cellIds[i]
      setProgress({ cellId, stages: [], queued: cellIds.slice(i + 1) })
      let outcome: CellRun
      try {
        outcome = await runCell(latestNotebook(), cellId, context, {
          failLastNode: consumeSimulatedFailure,
          signal: controller.signal,
          onProgress: (stages) => setProgress({ cellId, stages, queued: cellIds.slice(i + 1) }),
        })
      } catch {
        return // Interrupted: the page was left.
      }
      save(recordCellRun(latestNotebook(), cellId, outcome))
      if (outcome.status !== 'completed') break
    }
    setProgress(null)
  }

  const codeCells = notebook.cells.filter((c) => c.type === 'code')

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Exécution simulée (D1)">
          Le code n'est ni interprété, ni envoyé, ni exécuté : les contrôles avant envoi sont appliqués dans le navigateur
          et ne remplacent pas ceux des Hospital Nodes, puis les étapes Compute-to-Data sont simulées. Seul le code
          d'origine du notebook fictif renvoie son résultat de démonstration. Les modifications sont perdues au
          rechargement.
        </Alert>

        {access.contexts.length > 1 && (
          <SelectField
            label="Projet autorisé"
            value={context.summary.project.id}
            onChange={(e) => setSelectedId(e.target.value)}
            disabled={busy}
            options={access.contexts.map((c) => ({ value: c.summary.project.id, label: c.summary.project.title }))}
          />
        )}

        <div className="hc-stagger grid gap-6 lg:grid-cols-3">
          <div className="min-w-0 lg:col-span-2">
            <Card
              title={notebook.title}
              description={`${notebook.id} · ${context.summary.project.title}`}
              actions={
                <Button
                  onClick={() => run(codeCells.map((c) => c.id))}
                  disabled={busy || codeCells.length === 0}
                  loading={busy}
                >
                  Tout exécuter
                </Button>
              }
            >
              <div className="space-y-4">
                {notebook.cells.length === 0 ? (
                  <EmptyState title="Notebook vide" description="Ajoutez une cellule de code ou de texte." />
                ) : (
                  <ol aria-label="Cellules du notebook" className="space-y-4">
                    {notebook.cells.map((cell) => (
                      <CellView
                        key={cell.id}
                        cell={cell}
                        index={codeCells.indexOf(cell) + 1}
                        context={context}
                        progress={progress}
                        busy={busy}
                        onChange={(source) => save(updateCellSource(latestNotebook(), cell.id, source))}
                        onRun={() => run([cell.id])}
                        onRemove={() => save(removeCell(latestNotebook(), cell.id))}
                      />
                    ))}
                  </ol>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" size="sm" onClick={() => save(addCell(latestNotebook(), 'code'))} disabled={busy}>
                    + Code
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => save(addCell(latestNotebook(), 'markdown'))}
                    disabled={busy}
                  >
                    + Texte
                  </Button>
                </div>
              </div>
            </Card>
          </div>
          <div className="min-w-0">
            <AuthorizationContext context={context} />
          </div>
        </div>
      </div>
    </>
  )
}
