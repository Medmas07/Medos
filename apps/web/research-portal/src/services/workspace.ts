import type {
  CellCheck,
  CellRun,
  ComputeJobStage,
  GovernanceDecision,
  Notebook,
  NotebookCell,
  Organization,
  ProjectSummary,
  ResearchSnapshot,
} from '../types/research'
import { authorizationStatus, type AuthorizationStatus } from './dashboard'
import { requestedVariables, VARIABLE_CATALOG, type CatalogVariable } from './projectVariables'
import { FIXTURE_NOTEBOOKS, fixtureNotebookResult, isAuthorized } from './researchService'

/**
 * Colab-like research workspace (HC-099), MOCKED. Notebooks are edited in the
 * portal's session state only. Running a code cell applies deterministic
 * checks in the browser, then simulates the Compute-to-Data stages of the
 * fixture job (authorization check, execution in each Hospital Node,
 * aggregation, disclosure check): the code is never interpreted, sent, or
 * executed, and no Research Service, Governance Node, or Hospital Node is
 * contacted. Only an unchanged fixture cell returns its fixture controlled
 * result; edited or new code returns no computed aggregate.
 */

/** Packages a cell may import. `ctd` is the fictional Compute-to-Data API, preloaded in the environment. */
export const APPROVED_PACKAGES = ['ctd', 'numpy', 'pandas', 'scipy', 'statsmodels'] as const

/** Minimum cell size when the Governance decision does not state one; the HC-180 contract example uses 10. */
export const DEFAULT_MINIMUM_CELL_SIZE = 10

const GOVERNANCE_ORGANIZATION_ID = 'org-governance'
const PLATFORM_ORGANIZATION_ID = 'org-platform'

/** Everything a run is bound to: the authorized project, its decision, Hospital Nodes, scope, and output policy. */
export interface WorkspaceContext {
  summary: ProjectSummary
  decision: GovernanceDecision
  authorization: AuthorizationStatus
  /** Participating organizations with a Hospital Node, where the code would run. */
  nodes: Organization[]
  /** Participating organizations without a Hospital Node: nothing can run there. */
  withoutNode: Organization[]
  /** Authorized variables, matched to the catalog by name or fixture label. */
  variables: CatalogVariable[]
  /** Fixture variable labels the catalog does not know; they cannot be checked. */
  unmatchedVariables: string[]
  minimumCellSize: number
}

export type UnavailableReason = 'not_submitted' | 'under_review' | 'rejected' | 'expired'

export interface WorkspaceAccess {
  /** Projects with a still-valid Governance approval, most recent first. */
  contexts: WorkspaceContext[]
  /** Other projects and why the workspace is closed to them. */
  unavailable: { summary: ProjectSummary; reason: UnavailableReason }[]
}

/** The decision's minimum cell size ("Effectif minimal de 10…"), or the default. Pure. */
export function minimumCellSize(decision: GovernanceDecision): number {
  for (const condition of decision.conditions) {
    const match = /effectif minimal de (\d+)/i.exec(condition)
    if (match) return Number(match[1])
  }
  return DEFAULT_MINIMUM_CELL_SIZE
}

function unavailableReason(summary: ProjectSummary): UnavailableReason {
  if (!summary.request) return 'not_submitted'
  if (summary.request.status === 'rejected' || summary.decision?.outcome === 'rejected') return 'rejected'
  if (summary.request.status === 'under_review' || !summary.decision) return 'under_review'
  return 'expired'
}

/** Which projects may use the workspace at the snapshot's reference time. Pure. */
export function workspaceAccess(snapshot: ResearchSnapshot): WorkspaceAccess {
  const now = new Date(snapshot.asOf)
  const access: WorkspaceAccess = { contexts: [], unavailable: [] }
  for (const summary of snapshot.projects) {
    const authorization = authorizationStatus(summary, now)
    if (!isAuthorized(summary, now) || !authorization || !summary.decision) {
      access.unavailable.push({ summary, reason: unavailableReason(summary) })
      continue
    }
    const { entries, unmatched } = requestedVariables(summary.project)
    access.contexts.push({
      summary,
      decision: summary.decision,
      authorization,
      nodes: summary.participatingOrganizations.filter((o) => o.node),
      withoutNode: summary.participatingOrganizations.filter((o) => !o.node),
      variables: entries,
      unmatchedVariables: unmatched,
      minimumCellSize: minimumCellSize(summary.decision),
    })
  }
  return access
}

/** A starter notebook for an authorized project that has none yet. Pure. */
export function starterNotebook(context: WorkspaceContext): Notebook {
  const { project } = context.summary
  const id = `nb-${project.id}`
  const groupBy = context.variables[0]?.name ?? 'age_band'
  return {
    id,
    projectId: project.id,
    title: project.title,
    cells: [
      {
        id: `${id}-cell-1`,
        type: 'markdown',
        source: `## ${project.title}\nLe code est envoyé aux nœuds hospitaliers autorisés ; seules des statistiques agrégées reviennent.`,
      },
      {
        id: `${id}-cell-2`,
        type: 'code',
        source: `cohort = ctd.cohort()\nresult = cohort.group_by("${groupBy}").agg(participants="count")\nctd.release(result, min_cell_size=${context.minimumCellSize})`,
      },
    ],
  }
}

/** The project's notebook in the session, or a starter one. Pure. */
export function notebookFor(snapshot: ResearchSnapshot, context: WorkspaceContext): Notebook {
  return snapshot.notebooks.find((n) => n.projectId === context.summary.project.id) ?? starterNotebook(context)
}

/** The snapshot with this notebook added or replaced. Pure. */
export function withNotebook(snapshot: ResearchSnapshot, notebook: Notebook): ResearchSnapshot {
  const exists = snapshot.notebooks.some((n) => n.id === notebook.id)
  return {
    ...snapshot,
    notebooks: exists
      ? snapshot.notebooks.map((n) => (n.id === notebook.id ? notebook : n))
      : [...snapshot.notebooks, notebook],
  }
}

const mapCell = (notebook: Notebook, cellId: string, change: (cell: NotebookCell) => NotebookCell): Notebook => ({
  ...notebook,
  cells: notebook.cells.map((c) => (c.id === cellId ? change(c) : c)),
})

export const updateCellSource = (notebook: Notebook, cellId: string, source: string): Notebook =>
  mapCell(notebook, cellId, (c) => ({ ...c, source }))

export const recordCellRun = (notebook: Notebook, cellId: string, run: CellRun): Notebook =>
  mapCell(notebook, cellId, (c) => ({ ...c, lastRun: run }))

export const removeCell = (notebook: Notebook, cellId: string): Notebook => ({
  ...notebook,
  cells: notebook.cells.filter((c) => c.id !== cellId),
})

/** Adds an empty cell at the end, with the next `<notebook>-cell-N` identifier. Pure. */
export function addCell(notebook: Notebook, type: NotebookCell['type']): Notebook {
  const highest = notebook.cells.reduce(
    (max, c) => Math.max(max, Number(/-cell-(\d+)$/.exec(c.id)?.[1] ?? 0)),
    0,
  )
  return { ...notebook, cells: [...notebook.cells, { id: `${notebook.id}-cell-${highest + 1}`, type, source: '' }] }
}

/** Whether a run's output no longer matches the cell's source. */
export const isStale = (cell: NotebookCell) => cell.lastRun !== undefined && cell.lastRun.source !== cell.source

const SYSTEM_ACCESS = /\b(open|exec|eval|compile|__import__|input|breakpoint)\s*\(/

function importedModules(source: string): string[] {
  const modules: string[] = []
  for (const line of source.split('\n')) {
    const from = /^\s*from\s+([A-Za-z_][\w.]*)\s+import\b/.exec(line)
    if (from) {
      modules.push(from[1].split('.')[0])
      continue
    }
    const imported = /^\s*import\s+([^#]+)/.exec(line)
    if (imported) {
      for (const part of imported[1].split(',')) {
        const name = part.trim().split(/\s+/)[0]?.split('.')[0]
        if (name) modules.push(name)
      }
    }
  }
  return [...new Set(modules)]
}

/**
 * Deterministic checks of a code cell against the workspace context, at `now`.
 * They read the text only: they are not a sandbox, and the Hospital Node's and
 * Research Service's own checks would still apply. Pure.
 */
export function checkCell(source: string, context: WorkspaceContext, now: Date): CellCheck[] {
  const checks: CellCheck[] = []
  const authorized = isAuthorized(context.summary, now)
  checks.push({
    id: 'authorization',
    state: authorized ? 'passed' : 'failed',
    detail: authorized
      ? `Décision ${context.decision.id} valide.`
      : `La décision ${context.decision.id} n'est plus valide : aucune exécution sans nouvelle autorisation.`,
  })

  const code = source.trim()
  if (!code) {
    checks.push({ id: 'not_empty', state: 'failed', detail: 'La cellule est vide.' })
    return checks
  }

  const refused = importedModules(code).filter((m) => !(APPROVED_PACKAGES as readonly string[]).includes(m))
  checks.push({
    id: 'approved_packages',
    state: refused.length ? 'failed' : 'passed',
    detail: refused.length
      ? `Paquet(s) non approuvé(s) : ${refused.join(', ')}.`
      : 'Uniquement des paquets approuvés.',
  })

  const system = SYSTEM_ACCESS.exec(code)
  checks.push({
    id: 'no_system_access',
    state: system ? 'failed' : 'passed',
    detail: system
      ? `Appel interdit : ${system[1]}(). Fichiers, réseau et code dynamique sont exclus.`
      : 'Aucun accès aux fichiers, au réseau ou au code dynamique.',
  })

  const authorizedNames = new Set(context.variables.map((v) => v.name))
  const used = new Set([...code.matchAll(/["']([a-z][a-z0-9_]*)["']/g)].map((m) => m[1]))
  const outOfScope = VARIABLE_CATALOG.filter((v) => used.has(v.name) && !authorizedNames.has(v.name))
  checks.push({
    id: 'authorized_variables',
    state: outOfScope.length ? 'failed' : 'passed',
    detail: outOfScope.length
      ? `Variable(s) hors autorisation : ${outOfScope.map((v) => v.name).join(', ')}.`
      : 'Uniquement des variables autorisées.',
  })

  const releases = /\bctd\.release\s*\(/.test(code)
  const thresholds = [...code.matchAll(/\bmin_cell_size\s*=\s*(\d+)/g)].map((m) => Number(m[1]))
  const tooLow = thresholds.filter((n) => n < context.minimumCellSize)
  checks.push({
    id: 'minimum_cell_size',
    state: tooLow.length ? 'failed' : 'passed',
    detail: tooLow.length
      ? `Effectif minimal ${Math.min(...tooLow)} inférieur à celui de la décision (${context.minimumCellSize}).`
      : `Effectif minimal de ${context.minimumCellSize} par cellule appliqué.`,
  })

  checks.push({
    id: 'controlled_release',
    state: releases ? 'passed' : 'warning',
    detail: releases
      ? 'Sortie publiée par ctd.release, après contrôle de divulgation.'
      : 'Aucun appel à ctd.release : rien ne reviendra des Hospital Nodes.',
  })
  return checks
}

/** The source as a fixture notebook defines this cell, if it is one. */
function fixtureSource(notebookId: string, cellId: string): string | null {
  return FIXTURE_NOTEBOOKS.find((n) => n.id === notebookId)?.cells.find((c) => c.id === cellId)?.source ?? null
}

async function sha256Hex(text: string): Promise<string | null> {
  if (!globalThis.crypto?.subtle) return null
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

/** The simulated stages of a cell's run, all pending, in the order of the fixture job. Pure. */
export function plannedStages(context: WorkspaceContext, cellId: string, runNumber: number): ComputeJobStage[] {
  const prefix = `${cellId}-run-${runNumber}`
  return [
    { id: `${prefix}-auth`, stage: 'authorization_check', organizationId: GOVERNANCE_ORGANIZATION_ID, status: 'pending' },
    ...context.nodes.map(
      (o): ComputeJobStage => ({ id: `${prefix}-exec-${o.id}`, stage: 'execution', organizationId: o.id, status: 'pending' }),
    ),
    { id: `${prefix}-agg`, stage: 'aggregation', organizationId: PLATFORM_ORGANIZATION_ID, status: 'pending' },
    { id: `${prefix}-validation`, stage: 'output_validation', organizationId: PLATFORM_ORGANIZATION_ID, status: 'pending' },
  ]
}

export interface RunOptions {
  /** Time of the run, for the authorization check and timestamps. */
  now?: Date
  /** Simulated duration of each stage in milliseconds. */
  stageDelayMs?: number
  /** Demo scenario, asked once a cell passes its checks: whether the execution fails in the last Hospital Node. */
  failLastNode?: () => boolean
  /** Called with the stages each time one changes. */
  onProgress?: (stages: ComputeJobStage[]) => void
  /** Stops the simulation; the run then rejects. */
  signal?: AbortSignal
}

/**
 * Runs one code cell, MOCKED. A cell failing a check is refused before
 * anything is sent. Otherwise the stages are simulated one after the other; an
 * execution fails in a Hospital Node that is offline or whose DMI is
 * disconnected (or in the last one, in the failure scenario), and then no
 * result is released.
 */
export async function runCell(
  notebook: Notebook,
  cellId: string,
  context: WorkspaceContext,
  { now = new Date(), stageDelayMs = 600, failLastNode = () => false, onProgress, signal }: RunOptions = {},
): Promise<CellRun> {
  const cell = notebook.cells.find((c) => c.id === cellId)
  if (!cell || cell.type !== 'code') throw new Error(`Cellule de code inconnue : ${cellId}.`)

  const number = (cell.lastRun?.number ?? 0) + 1
  const startedAt = now.toISOString()
  const checks = checkCell(cell.source, context, now)
  const algorithmSha256 = await sha256Hex(cell.source)
  const base = { number, source: cell.source, algorithmSha256, startedAt, checks }

  const failed = checks.filter((c) => c.state === 'failed')
  if (failed.length > 0) {
    return {
      ...base,
      finishedAt: startedAt,
      status: 'refused',
      stages: [],
      output: { kind: 'none' },
      error: 'Cellule non envoyée : ' + failed.map((c) => c.detail).join(' '),
    }
  }
  if (context.nodes.length === 0) {
    return {
      ...base,
      finishedAt: startedAt,
      status: 'refused',
      stages: [],
      output: { kind: 'none' },
      error: "Cellule non envoyée : aucun établissement participant n'a de Hospital Node.",
    }
  }

  const failingNode = failLastNode() ? context.nodes.at(-1) : undefined
  let stages = plannedStages(context, cellId, number)
  let elapsed = 0
  const set = (index: number, change: Partial<ComputeJobStage>) => {
    stages = stages.map((s, i) => (i === index ? { ...s, ...change } : s))
    onProgress?.(stages)
  }
  const wait = () =>
    new Promise<void>((resolve, reject) => {
      if (signal?.aborted) return reject(new Error('Exécution simulée interrompue.'))
      const timer = setTimeout(resolve, stageDelayMs)
      signal?.addEventListener(
        'abort',
        () => {
          clearTimeout(timer)
          reject(new Error('Exécution simulée interrompue.'))
        },
        { once: true },
      )
    })
  const at = () => new Date(now.getTime() + elapsed).toISOString()

  onProgress?.(stages)
  for (let i = 0; i < stages.length; i++) {
    set(i, { status: 'running' })
    await wait()
    elapsed += stageDelayMs
    const node = context.nodes.find((o) => o.id === stages[i].organizationId)
    const nodeFails =
      stages[i].stage === 'execution' &&
      node !== undefined &&
      (node.node?.status === 'offline' ||
        node.node?.dmiState === 'disconnected' ||
        node === failingNode)
    if (nodeFails) {
      set(i, { status: 'failed', completedAt: at() })
      return {
        ...base,
        finishedAt: at(),
        status: 'failed',
        stages,
        output: { kind: 'none' },
        error: `L'exécution locale n'a pas abouti dans ${node.shortName} (${node.node?.id}). Aucun résultat, même partiel, n'est publié.`,
      }
    }
    set(i, { status: 'completed', completedAt: at() })
  }

  const releases = checks.some((c) => c.id === 'controlled_release' && c.state === 'passed')
  const fixture = fixtureSource(notebook.id, cellId) === cell.source ? fixtureNotebookResult(notebook.id) : null
  return {
    ...base,
    finishedAt: at(),
    status: 'completed',
    stages,
    output: !releases ? { kind: 'no_release' } : fixture ? { kind: 'aggregate', ...fixture } : { kind: 'not_simulated' },
  }
}
