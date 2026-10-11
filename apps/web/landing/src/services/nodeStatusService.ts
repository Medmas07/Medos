import type { NodeSummary, OnboardingSnapshot } from '../types/onboarding'
import { nodeConfiguration } from './nodeConfigService'
import { INSTALLATION_STEP_COUNT } from './onboardingService'

/**
 * Hospital Node status dashboard (HC-063). MOCKED: the portal displays the Node
 * summary it was given (fixtures or a demo scenario); it never contacts the
 * Hospital Node, its DMI, or the Federation Service. No health-status contract
 * exists yet. Every state below is derived deterministically from that summary,
 * with no time threshold, because no requirement defines one.
 */

/**
 * Version reported by the Hospital Node runtime (`NODE_VERSION` in
 * `instances/hospital-node/application/get_node_status.py`); a test fails if they drift.
 */
export const LATEST_NODE_VERSION = '0.3.0'

export type IndicatorState = 'ok' | 'warning' | 'critical' | 'unknown'

export type IndicatorId = 'connectivity' | 'dmi' | 'version' | 'health' | 'synchronization'

export interface NodeIndicator {
  id: IndicatorId
  label: string
  state: IndicatorState
  /** Short value, for example "En ligne" or "0.3.0". */
  value: string
  detail: string
  /** Time the value refers to, for example the last synchronization. */
  at?: string
}

export interface HealthCheck {
  id: 'liveness' | 'local-storage' | 'dmi-adapter' | 'federation'
  label: string
  state: IndicatorState
  detail: string
}

export interface NodeStatusReport {
  node: NodeSummary
  indicators: NodeIndicator[]
  healthChecks: HealthCheck[]
}

export type NodeStatusAvailability =
  | { kind: 'not_approved' }
  | { kind: 'not_installed'; declaredSteps: number }
  | { kind: 'ready'; report: NodeStatusReport }

/** Compares dotted numeric versions; negative when `a` is older. Pure. */
export function compareVersions(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] ?? 0) - (pb[i] ?? 0)
    if (diff !== 0) return diff
  }
  return 0
}

function healthChecks(node: NodeSummary): HealthCheck[] {
  if (node.status === 'offline') {
    const unknown = 'Aucune réponse du nœud : résultat inconnu.'
    return [
      { id: 'liveness', label: 'Vivacité (GET /health)', state: 'critical', detail: 'Le nœud ne répond pas.' },
      { id: 'local-storage', label: 'Stockage local', state: 'unknown', detail: unknown },
      { id: 'dmi-adapter', label: 'Adaptateur DMI', state: 'unknown', detail: unknown },
      { id: 'federation', label: 'Registre de fédération', state: 'unknown', detail: unknown },
    ]
  }
  return [
    { id: 'liveness', label: 'Vivacité (GET /health)', state: 'ok', detail: 'Le nœud répond.' },
    { id: 'local-storage', label: 'Stockage local', state: 'ok', detail: 'Accessible par le nœud.' },
    node.dmiState === 'connected'
      ? { id: 'dmi-adapter', label: 'Adaptateur DMI', state: 'ok', detail: 'Connecté au DMI local.' }
      : { id: 'dmi-adapter', label: 'Adaptateur DMI', state: 'critical', detail: 'Déconnecté du DMI local.' },
    { id: 'federation', label: 'Registre de fédération', state: 'ok', detail: 'Nœud inscrit au registre.' },
  ]
}

/** Builds the dashboard from a Node summary. Pure. */
export function nodeStatusReport(node: NodeSummary): NodeStatusReport {
  const offline = node.status === 'offline'
  const checks = healthChecks(node)
  const passed = checks.filter((c) => c.state === 'ok').length
  const versionDiff = compareVersions(node.version, LATEST_NODE_VERSION)

  const connectivity: NodeIndicator =
    node.status === 'online'
      ? { id: 'connectivity', label: 'Connectivité', state: 'ok', value: 'En ligne', detail: 'Le nœud répond normalement.' }
      : node.status === 'degraded'
        ? {
            id: 'connectivity',
            label: 'Connectivité',
            state: 'warning',
            value: 'Dégradé',
            detail: 'Le nœud répond, mais au moins un contrôle échoue.',
          }
        : {
            id: 'connectivity',
            label: 'Connectivité',
            state: 'critical',
            value: 'Hors ligne',
            detail: 'Le nœud ne répond pas ; les autres états sont les derniers connus.',
          }

  const dmi: NodeIndicator = offline
    ? {
        id: 'dmi',
        label: 'Adaptateur DMI',
        state: 'unknown',
        value: 'Inconnu',
        detail: `Dernier état connu : ${node.dmiState === 'connected' ? 'connecté' : 'déconnecté'}.`,
      }
    : node.dmiState === 'connected'
      ? { id: 'dmi', label: 'Adaptateur DMI', state: 'ok', value: 'Connecté', detail: 'L’adaptateur local du nœud joint le DMI.' }
      : {
          id: 'dmi',
          label: 'Adaptateur DMI',
          state: 'critical',
          value: 'Déconnecté',
          detail: 'L’adaptateur local du nœud ne joint plus le DMI : à vérifier par votre équipe sur site.',
        }

  const version: NodeIndicator =
    versionDiff < 0
      ? {
          id: 'version',
          label: 'Version',
          state: 'warning',
          value: node.version,
          detail: `Version ${LATEST_NODE_VERSION} disponible.`,
        }
      : { id: 'version', label: 'Version', state: 'ok', value: node.version, detail: 'Version la plus récente.' }

  const health: NodeIndicator = {
    id: 'health',
    label: 'Contrôles de santé',
    state: offline ? 'critical' : passed === checks.length ? 'ok' : 'warning',
    value: `${passed} / ${checks.length}`,
    detail: offline ? 'Aucun contrôle n’a pu être exécuté.' : `${passed} contrôle(s) réussi(s) sur ${checks.length}.`,
  }

  const synchronization: NodeIndicator = offline
    ? {
        id: 'synchronization',
        label: 'Synchronisation',
        state: 'unknown',
        value: 'Inconnue',
        detail: 'Le nœud ne répond pas ; dernière synchronisation connue :',
        at: node.lastSyncAt,
      }
    : node.dmiState === 'disconnected'
      ? {
          id: 'synchronization',
          label: 'Synchronisation',
          state: 'warning',
          value: 'Interrompue',
          detail: 'Interrompue tant que l’adaptateur DMI est déconnecté ; dernière synchronisation :',
          at: node.lastSyncAt,
        }
      : {
          id: 'synchronization',
          label: 'Synchronisation',
          state: 'ok',
          value: 'À jour',
          detail: 'Dernière synchronisation :',
          at: node.lastSyncAt,
        }

  return { node, indicators: [connectivity, dmi, version, health, synchronization], healthChecks: checks }
}

/** What the dashboard can show for this snapshot. Pure. */
export function nodeStatus(snapshot: OnboardingSnapshot): NodeStatusAvailability {
  if (nodeConfiguration(snapshot).kind !== 'ready') return { kind: 'not_approved' }
  const node = snapshot.organization.node
  if (!node) {
    return { kind: 'not_installed', declaredSteps: snapshot.application?.installationChecklist?.length ?? 0 }
  }
  return { kind: 'ready', report: nodeStatusReport(node) }
}

export interface RefreshOptions {
  /** Simulates an unavailable status service (demo scenario). */
  simulateFailure?: boolean
  delayMs?: number
  now?: Date
}

/**
 * Simulated refresh. With no health-status contract yet, it returns the state
 * already known, with the time it was checked. It never contacts the Node.
 */
export async function refreshNodeStatus(
  snapshot: OnboardingSnapshot,
  { simulateFailure = false, delayMs = 600, now = new Date() }: RefreshOptions = {},
): Promise<{ status: NodeStatusAvailability; checkedAt: string }> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  if (simulateFailure) {
    throw new Error("L'état du nœud n'a pas pu être actualisé : service de supervision simulé indisponible (scénario de démonstration).")
  }
  return { status: nodeStatus(snapshot), checkedAt: now.toISOString() }
}

export { INSTALLATION_STEP_COUNT }
