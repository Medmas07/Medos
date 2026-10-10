import type { Tone } from '@hackcure/design-system'
import type {
  ActionPriority,
  AuthorizationState,
  LifecycleStep,
  LifecycleStepId,
  NextActionKind,
  StepState,
} from './services/dashboard'
import type { ExecutionPhaseId } from './services/executions'
import type { RequestState, TrackingStepId } from './services/requestTracking'
import type { WithheldReason } from './services/results'
import type { UnavailableReason } from './services/workspace'
import type {
  CellCheck,
  CellRun,
  ComputeJob,
  ComputeJobStage,
  PageStatus,
  ResearchAccessRequest,
  SciAgentsCitation,
  SciAgentsHypothesis,
  SciAgentsInvestigation,
} from './types/research'

export const requestStatusDisplay: Record<
  ResearchAccessRequest['status'] | 'not_submitted' | 'expired',
  { label: string; tone: Tone }
> = {
  not_submitted: { label: 'Non soumise', tone: 'neutral' },
  expired: { label: 'Expirée', tone: 'warning' },
  under_review: { label: 'En revue', tone: 'info' },
  approved: { label: 'Autorisée', tone: 'success' },
  rejected: { label: 'Refusée', tone: 'danger' },
}

export const pageStatusDisplay: Record<PageStatus, { label: string; tone: Tone }> = {
  available: { label: 'Accessible', tone: 'neutral' },
  locked: { label: 'Verrouillé', tone: 'neutral' },
}

const dateFormat = new Intl.DateTimeFormat('fr-TN', { dateStyle: 'medium', timeZone: 'Africa/Tunis' })

const dateTimeFormat = new Intl.DateTimeFormat('fr-TN', {
  dateStyle: 'medium',
  timeStyle: 'short',
  hourCycle: 'h23',
  timeZone: 'Africa/Tunis',
})

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso))
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}

export const jobStatusDisplay: Record<ComputeJob['status'], { label: string; tone: Tone }> = {
  queued: { label: 'En file', tone: 'neutral' },
  running: { label: 'En cours', tone: 'info' },
  completed: { label: 'Terminée', tone: 'success' },
  failed: { label: 'Échouée', tone: 'danger' },
}

export const authorizationDisplay: Record<AuthorizationState, { label: string; tone: Tone }> = {
  valid: { label: 'Valide', tone: 'success' },
  expiring: { label: 'Expire bientôt', tone: 'warning' },
  expired: { label: 'Expirée', tone: 'warning' },
}

export const priorityDisplay: Record<ActionPriority, { label: string; tone: Tone }> = {
  attention: { label: 'Action requise', tone: 'warning' },
  ready: { label: 'À faire', tone: 'info' },
  waiting: { label: 'En attente', tone: 'neutral' },
}

export const stepStateTone: Record<StepState, Tone> = {
  done: 'success',
  current: 'info',
  blocked: 'warning',
  upcoming: 'neutral',
}

export const lifecycleStepLabels: Record<LifecycleStepId, string> = {
  project: 'Projet',
  request: "Demande d'accès",
  decision: 'Décision de gouvernance',
  execution: 'Exécution Compute-to-Data',
  result: 'Résultat contrôlé',
}

export const nextActionDisplay: Record<NextActionKind, { title: string; description: string; cta: string }> = {
  submit_request: {
    title: "Soumettre la demande d'accès",
    description: "Le projet n'a pas encore été soumis à l'Autorité de gouvernance et d'éthique.",
    cta: 'Préparer la demande',
  },
  await_decision: {
    title: "Décision de l'Autorité de gouvernance attendue",
    description: "La demande est en revue. Ni ce portail ni l'opérateur de la plateforme ne peuvent l'autoriser.",
    cta: 'Suivre la demande',
  },
  request_rejected: {
    title: 'Demande refusée',
    description: "Consultez la motivation de l'Autorité de gouvernance avant toute nouvelle demande.",
    cta: 'Voir la décision',
  },
  renew_request: {
    title: 'Autorisation expirée',
    description: "Aucune nouvelle exécution n'est possible sans une nouvelle autorisation de gouvernance.",
    cta: 'Préparer une nouvelle demande',
  },
  prepare_execution: {
    title: 'Préparer une exécution',
    description: 'Le projet est autorisé : écrivez le code qui sera envoyé aux Hospital Nodes participants.',
    cta: "Ouvrir l'espace de travail",
  },
  follow_execution: {
    title: "Suivre l'exécution",
    description: "Le code s'exécute dans les Hospital Nodes autorisés.",
    cta: 'Voir les exécutions',
  },
  execution_failed: {
    title: 'Exécution échouée',
    description: "Consultez les étapes de l'exécution pour identifier le nœud ou le contrôle en échec.",
    cta: 'Voir les exécutions',
  },
  await_result: {
    title: 'Résultat en cours de contrôle',
    description: "L'agrégat est soumis au contrôle de divulgation avant sa mise à disposition.",
    cta: 'Voir les résultats',
  },
  review_result: {
    title: 'Consulter le résultat contrôlé',
    description: 'Un résultat agrégé a passé le contrôle de divulgation.',
    cta: 'Voir le résultat',
  },
}

export const stepReasonLabels: Record<NonNullable<LifecycleStep['reason']>, string> = {
  rejected: 'Refusée',
  expired: 'Expirée',
  failed: 'Échouée',
  disclosure_failed: 'Contrôle de divulgation échoué',
}

export const requestStateDisplay: Record<RequestState, { label: string; tone: Tone }> = {
  under_review: { label: 'En revue', tone: 'info' },
  approved: { label: 'Autorisée', tone: 'success' },
  expiring: { label: 'Autorisée, expire bientôt', tone: 'warning' },
  expired: { label: 'Autorisation expirée', tone: 'warning' },
  rejected: { label: 'Refusée', tone: 'danger' },
}

export const trackingStepLabels: Record<TrackingStepId, string> = {
  submitted: 'Demande soumise',
  review: "Examen par l'Autorité de gouvernance et d'éthique",
  decision: "Décision de l'Autorité",
}

export const cellRunDisplay: Record<CellRun['status'] | 'queued' | 'running', { label: string; tone: Tone }> = {
  queued: { label: 'En file', tone: 'neutral' },
  running: { label: 'En cours', tone: 'info' },
  completed: { label: 'Terminée', tone: 'success' },
  refused: { label: 'Refusée', tone: 'warning' },
  failed: { label: 'Échouée', tone: 'danger' },
}

export const cellCheckLabels: Record<CellCheck['id'], string> = {
  authorization: 'Autorisation de gouvernance',
  not_empty: 'Code présent',
  approved_packages: 'Paquets approuvés',
  no_system_access: 'Accès système',
  authorized_variables: 'Variables autorisées',
  minimum_cell_size: 'Effectif minimal',
  controlled_release: 'Sortie contrôlée',
}

export const cellCheckTone: Record<CellCheck['state'], Tone> = {
  passed: 'success',
  warning: 'warning',
  failed: 'danger',
}

export const stageStatusTone: Record<ComputeJobStage['status'], Tone> = {
  pending: 'neutral',
  running: 'info',
  completed: 'success',
  failed: 'danger',
}

export const stageStatusLabels: Record<ComputeJobStage['status'], string> = {
  pending: 'À venir',
  running: 'En cours',
  completed: 'Terminé',
  failed: 'Échec',
}

export const unavailableReasonDisplay: Record<UnavailableReason, { label: string; tone: Tone }> = {
  not_submitted: { label: 'Demande non soumise', tone: 'neutral' },
  under_review: { label: 'En revue', tone: 'info' },
  rejected: { label: 'Refusée', tone: 'danger' },
  expired: { label: 'Autorisation expirée', tone: 'warning' },
}

/** An aggregate cell: numbers in French notation with the column's `decimals`, text as is. */
export function formatCell(value: string | number, decimals = 0): string {
  if (typeof value !== 'number') return value
  return new Intl.NumberFormat('fr-TN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)
}

/** The most decimals among a column's numbers, so that its values align. */
export function columnDecimals(values: (string | number)[]): number {
  return Math.max(0, ...values.map((v) => (typeof v === 'number' ? (String(v).split('.')[1]?.length ?? 0) : 0)))
}

export const withheldReasonDisplay: Record<WithheldReason, { label: string; tone: Tone; detail: string }> = {
  in_progress: {
    label: 'En cours',
    tone: 'info',
    detail: "Le résultat n'est publié qu'après l'agrégation et le contrôle de divulgation.",
  },
  failed: {
    label: 'Échouée',
    tone: 'danger',
    detail: "Une étape a échoué : aucun résultat, même partiel, n'est publié.",
  },
  no_release: {
    label: 'Sans ctd.release',
    tone: 'neutral',
    detail: "Le code n'appelle pas ctd.release : rien n'a quitté les Hospital Nodes.",
  },
  not_simulated: {
    label: 'Non calculé',
    tone: 'demo',
    detail: "Le code modifié ou nouveau n'est pas interprété dans cette démonstration : aucun agrégat n'est calculé.",
  },
}

export const executionPhaseDisplay: Record<ExecutionPhaseId, { title: string; description: string }> = {
  submitted: {
    title: 'Soumise',
    description: "Le code de l'analyse est soumis avec la référence de son autorisation.",
  },
  authorization: {
    title: 'Autorisée par la gouvernance',
    description: 'Le Governance Node vérifie que la décision est valide et couvre ce périmètre.',
  },
  execution: {
    title: 'Exécution dans les Hospital Nodes',
    description: "Le code s'exécute localement dans chaque nœud autorisé, en parallèle.",
  },
  aggregation: {
    title: 'Agrégation',
    description: 'Seuls les agrégats produits par les nœuds sont combinés.',
  },
  completed: {
    title: 'Terminée',
    description: "Contrôle de divulgation (effectif minimal) avant toute mise à disposition.",
  },
}

export const investigationStatusDisplay: Record<SciAgentsInvestigation['status'], { label: string; tone: Tone }> = {
  queued: { label: 'En file', tone: 'neutral' },
  running: { label: 'En cours', tone: 'info' },
  completed: { label: 'Terminée', tone: 'success' },
  failed: { label: 'Échouée', tone: 'danger' },
}

/** Confidence as SciAgents reports it: never a validation of the hypothesis. */
export const confidenceDisplay: Record<NonNullable<SciAgentsHypothesis['confidence']> | 'unknown', { label: string; tone: Tone }> = {
  low: { label: 'Confiance faible', tone: 'neutral' },
  moderate: { label: 'Confiance modérée', tone: 'info' },
  high: { label: 'Confiance élevée', tone: 'info' },
  unknown: { label: 'Confiance non communiquée', tone: 'neutral' },
}

export const citationKindLabels: Record<SciAgentsCitation['kind'], string> = {
  publication: 'Publication',
  controlled_result: 'Résultat contrôlé',
  other: 'Autre source',
}

export const investigationErrorLabels: Record<NonNullable<SciAgentsInvestigation['error']>['code'], string> = {
  upstream_unavailable: 'SciAgents indisponible',
  upstream_error: 'Erreur de SciAgents',
  timeout: "Délai d'attente dépassé",
  rejected_by_upstream: 'Refusée par SciAgents',
}
