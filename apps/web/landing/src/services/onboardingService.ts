import governanceFixtures from '../../../../../demo-data/governance.json'
import notificationFixtures from '../../../../../demo-data/notifications.json'
import organizationFixtures from '../../../../../demo-data/organizations.json'
import peopleFixtures from '../../../../../demo-data/people.json'
import type {
  GovernanceDecision,
  HospitalApplication,
  NodeSummary,
  OnboardingSnapshot,
  OnboardingStep,
  Organization,
  PortalNotification,
  StaffMember,
  StepId,
} from '../types/onboarding'
import { nodeRefFor } from './nodeConfigService'

/**
 * MOCKED onboarding service. It reads the canonical fictional fixtures in the
 * browser and simulates latency; there is no onboarding API yet. The portal only
 * displays Governance decisions: nothing here can approve an application.
 */

const applications = governanceFixtures.hospitalApplications as unknown as HospitalApplication[]
const organizations = organizationFixtures.organizations as unknown as Organization[]
const staff = peopleFixtures.staff as unknown as StaffMember[]
const notifications = notificationFixtures.notifications as unknown as PortalNotification[]
const decisions = (governanceFixtures.decisions as unknown as (GovernanceDecision | { subjectType: string })[]).filter(
  (d): d is GovernanceDecision => d.subjectType === 'hospital_application',
)

/** Read-only fixture views reused by the registration mock. */
export function listOrganizations(): readonly Organization[] {
  return organizations
}

/** Demo persona: the fictional manager of Centre Hospitalier Cap Azur (in onboarding). */
export const DEMO_ORGANIZATION_ID = 'org-hospital-c'
export const DEMO_MANAGER_ID = 'usr-mehdi'

export type StepSection = 'onboarding' | 'node'

export interface StepDefinition {
  id: StepId
  label: string
  /** Shorter label for the sidebar, where a status badge shares the row. */
  navLabel: string
  ticket: string
  section: StepSection
}

/** Portal pages in workflow order, as in the product vision's onboarding workflow. */
export const STEP_DEFINITIONS: readonly StepDefinition[] = [
  { id: 'registration', label: 'Inscription', navLabel: 'Inscription', ticket: 'HC-051', section: 'onboarding' },
  { id: 'profile', label: "Profil de l'établissement", navLabel: 'Profil', ticket: 'HC-052', section: 'onboarding' },
  { id: 'documents', label: 'Documents administratifs', navLabel: 'Documents', ticket: 'HC-053', section: 'onboarding' },
  { id: 'agreements', label: 'Accords', navLabel: 'Accords', ticket: 'HC-054', section: 'onboarding' },
  { id: 'technical', label: 'Questionnaire technique', navLabel: 'Questionnaire technique', ticket: 'HC-055', section: 'onboarding' },
  { id: 'dmi', label: 'Questionnaire DMI / SIH', navLabel: 'DMI / SIH', ticket: 'HC-056', section: 'onboarding' },
  { id: 'automated-review', label: 'Revue automatisée', navLabel: 'Contrôles', ticket: 'HC-057', section: 'onboarding' },
  { id: 'human-review', label: 'Validation humaine', navLabel: 'Revue humaine', ticket: 'HC-058', section: 'onboarding' },
  { id: 'decision', label: 'Décision de gouvernance', navLabel: 'Décision', ticket: 'HC-059', section: 'onboarding' },
  { id: 'node-configuration', label: 'Configuration du nœud', navLabel: 'Configuration', ticket: 'HC-060', section: 'node' },
  { id: 'node-download', label: 'Téléchargement du nœud', navLabel: 'Téléchargement', ticket: 'HC-061', section: 'node' },
  { id: 'node-installation', label: "Guide d'installation", navLabel: 'Installation', ticket: 'HC-062', section: 'node' },
  { id: 'node-status', label: 'État du nœud', navLabel: 'État du nœud', ticket: 'HC-063', section: 'node' },
]

const LOCKED_DETAIL = "Disponible après approbation par l'Autorité de gouvernance."

type StepState = Pick<OnboardingStep, 'status' | 'detail'>

function plural(count: number, word: string): string {
  return `${count} ${word}${count > 1 ? 's' : ''}`
}

function documentsState(application: HospitalApplication): StepState {
  const total = application.documents.length
  const missing = application.documents.filter((d) => d.status !== 'received').length
  if (total === 0 || missing === total) return { status: 'pending', detail: 'Aucun document déposé.' }
  if (missing > 0 && application.status === 'draft') {
    return { status: 'in_progress', detail: `${total - missing} / ${total} documents déposés.` }
  }
  if (missing > 0) return { status: 'attention', detail: `${plural(missing, 'document')} à fournir.` }
  return { status: 'completed', detail: `${plural(application.documents.length, 'document')} reçu(s).` }
}

function agreementsState(application: HospitalApplication): StepState {
  const total = application.agreements.length
  const open = application.agreements.filter((a) => !a.accepted).length
  if (total === 0 || open === total) return { status: 'pending', detail: 'Aucun accord accepté.' }
  if (open > 0 && application.status === 'draft') {
    return { status: 'in_progress', detail: `${total - open} / ${total} accords acceptés.` }
  }
  if (open > 0) return { status: 'attention', detail: `${plural(open, 'accord')} non accepté(s).` }
  return { status: 'completed', detail: 'Tous les accords sont acceptés.' }
}

function automatedReviewState(application: HospitalApplication): StepState {
  const completeness = application.reviewSteps.find((s) => s.step === 'completeness_check')
  const assisted = application.reviewSteps.find((s) => s.step === 'assisted_review')
  if (!completeness || completeness.status === 'pending') {
    return { status: 'pending', detail: 'Vérifications automatiques non lancées.' }
  }
  // Only completeness findings require action; assisted-review remarks are advisory.
  if (completeness.findings.length > 0) {
    return { status: 'attention', detail: `Complétude : ${plural(completeness.findings.length, 'point')} à corriger.` }
  }
  const remarks = assisted?.findings.length ?? 0
  return remarks > 0
    ? { status: 'completed', detail: `Dossier complet ; ${plural(remarks, 'remarque')} indicative(s).` }
    : { status: 'completed', detail: 'Dossier complet, sans remarque.' }
}

function humanReviewState(application: HospitalApplication): StepState {
  const step = application.reviewSteps.find((s) => s.step === 'human_review')
  if (!step) return { status: 'pending', detail: 'Pas encore transmise en revue humaine.' }
  if (step.status === 'pending') {
    return { status: 'in_progress', detail: "En cours auprès de l'Autorité de gouvernance." }
  }
  return { status: 'completed', detail: "Revue humaine terminée par l'Autorité de gouvernance." }
}

function profileState(application: HospitalApplication): StepState {
  const profile = application.administrativeProfile
  if (!profile) {
    return application.status === 'draft'
      ? { status: 'pending', detail: 'Informations administratives à compléter.' }
      : { status: 'completed', detail: 'Profil renseigné.' }
  }
  return profile.securityContact
    ? { status: 'completed', detail: 'Profil renseigné.' }
    : { status: 'completed', detail: 'Profil renseigné, sans contact sécurité distinct.' }
}

/** Number of steps in the installation guide (HC-062). */
export const INSTALLATION_STEP_COUNT = 9

function installationState(done: string[]): StepState {
  if (done.length === 0) return { status: 'pending', detail: 'Installation non commencée.' }
  if (done.length < INSTALLATION_STEP_COUNT) {
    return { status: 'in_progress', detail: `${done.length} / ${INSTALLATION_STEP_COUNT} étapes déclarées effectuées.` }
  }
  return { status: 'completed', detail: 'Installation déclarée terminée (non vérifiée).' }
}

/** Derives the display state of every portal step from fixture data. Pure. */
export function deriveSteps(
  organization: Organization,
  application: HospitalApplication | null,
): OnboardingStep[] {
  const states = new Map<StepId, StepState>()

  if (!application) {
    states.set('registration', { status: 'pending', detail: 'Aucune candidature soumise.' })
  } else if (application.status === 'approved') {
    for (const def of STEP_DEFINITIONS) {
      if (def.section === 'onboarding') states.set(def.id, { status: 'completed', detail: 'Terminé.' })
    }
    states.set('decision', { status: 'completed', detail: "Approuvé par l'Autorité de gouvernance." })
    // Approval may leave documents to provide (decision conditions); show them.
    const documents = documentsState(application)
    if (documents.status === 'attention') states.set('documents', documents)
    const node = organization.node
    const delivered: StepState = node
      ? { status: 'completed', detail: `Nœud ${node.id} (v${node.version}).` }
      : { status: 'pending', detail: 'Configuration non générée.' }
    // Without an installed node, approval makes the configuration ready (HC-060);
    // download and installation remain to do.
    states.set(
      'node-configuration',
      node ? delivered : { status: 'completed', detail: `Configuration prête : ${nodeRefFor(organization.id)}.` },
    )
    states.set(
      'node-download',
      node
        ? delivered
        : application.nodePackage
          ? { status: 'completed', detail: `Package téléchargé : ${application.nodePackage.fileName}.` }
          : { status: 'pending', detail: 'Package non téléchargé.' },
    )
    states.set('node-installation', node ? delivered : installationState(application.installationChecklist ?? []))
    states.set(
      'node-status',
      !node
        ? { status: 'pending', detail: 'Nœud non installé.' }
        : node.status === 'online'
          ? { status: 'completed', detail: 'Nœud en ligne.' }
          : { status: 'attention', detail: `Nœud ${node.status === 'degraded' ? 'dégradé' : 'hors ligne'}.` },
    )
  } else {
    const questionnaire = application.technicalQuestionnaire
    const draft = application.status === 'draft'
    states.set('registration', {
      status: 'completed',
      detail: draft ? `Inscription enregistrée (${application.id}).` : 'Candidature soumise.',
    })
    states.set('profile', profileState(application))
    states.set('documents', documentsState(application))
    states.set('agreements', agreementsState(application))
    states.set(
      'technical',
      questionnaire
        ? { status: 'completed', detail: 'Questionnaire complété.' }
        : { status: 'pending', detail: 'Questionnaire non complété.' },
    )
    states.set(
      'dmi',
      questionnaire?.dmiSystem && questionnaire.integrationMethods?.length
        ? { status: 'completed', detail: `DMI déclaré : ${questionnaire.dmiSystem}.` }
        : { status: 'pending', detail: 'DMI / SIH non décrit.' },
    )
    states.set('automated-review', automatedReviewState(application))
    states.set('human-review', humanReviewState(application))
    states.set(
      'decision',
      application.status === 'rejected'
        ? { status: 'rejected', detail: "Candidature rejetée par l'Autorité de gouvernance." }
        : { status: 'pending', detail: "Décision de l'Autorité de gouvernance attendue." },
    )
    if (application.status === 'rejected') {
      // Nothing can change after a rejection: open steps must not ask for action.
      for (const [id, state] of states) {
        if (id !== 'decision' && state.status !== 'completed') {
          states.set(id, { status: 'locked', detail: 'Verrouillé : candidature rejetée.' })
        }
      }
    }
  }

  return STEP_DEFINITIONS.map((def) => {
    const fallback: StepState =
      def.section === 'node'
        ? { status: 'locked', detail: LOCKED_DETAIL }
        : { status: 'pending', detail: 'Non commencé.' }
    return { id: def.id, label: def.label, ticket: def.ticket, ...(states.get(def.id) ?? fallback) }
  })
}

/**
 * Demo scenarios, selected with `?demo=vide`, `?demo=erreur`,
 * `?demo=echec-inscription`, `?demo=echec-profil`, `?demo=echec-document`,
 * `?demo=echec-accord`, `?demo=echec-technique`, `?demo=echec-dmi`,
 * `?demo=echec-soumission`, or `?demo=echec-actualisation` in the URL. The
 * document and refresh failure scenarios start like `nominal`; the other
 * failure scenarios start like `empty`. Each makes the first matching request
 * fail. `?demo=decision-approuvee` and `?demo=decision-refusee` start like
 * `nominal` and simulate a Governance decision published for the application.
 * `?demo=echec-telechargement` starts like `decision-approuvee`, and the first
 * Node package preparation fails. `?demo=noeud-en-ligne`, `?demo=noeud-degrade`,
 * and `?demo=noeud-hors-ligne` start like `decision-approuvee` and simulate an
 * installed Hospital Node reporting that state; `?demo=echec-etat-noeud` starts
 * like `noeud-en-ligne`, and the first status refresh fails.
 */
export type DemoScenario =
  | 'nominal'
  | 'empty'
  | 'error'
  | 'registration-failure'
  | 'profile-failure'
  | 'document-failure'
  | 'agreement-failure'
  | 'technical-failure'
  | 'dmi-failure'
  | 'submission-failure'
  | 'refresh-failure'
  | 'decision-approved'
  | 'decision-rejected'
  | 'download-failure'
  | 'node-online'
  | 'node-degraded'
  | 'node-offline'
  | 'node-status-failure'

export function scenarioFromSearch(search: string): DemoScenario {
  const value = new URLSearchParams(search).get('demo')
  if (value === 'vide') return 'empty'
  if (value === 'erreur') return 'error'
  if (value === 'echec-inscription') return 'registration-failure'
  if (value === 'echec-profil') return 'profile-failure'
  if (value === 'echec-document') return 'document-failure'
  if (value === 'echec-accord') return 'agreement-failure'
  if (value === 'echec-technique') return 'technical-failure'
  if (value === 'echec-dmi') return 'dmi-failure'
  if (value === 'echec-soumission') return 'submission-failure'
  if (value === 'echec-actualisation') return 'refresh-failure'
  if (value === 'decision-approuvee') return 'decision-approved'
  if (value === 'decision-refusee') return 'decision-rejected'
  if (value === 'echec-telechargement') return 'download-failure'
  if (value === 'noeud-en-ligne') return 'node-online'
  if (value === 'noeud-degrade') return 'node-degraded'
  if (value === 'noeud-hors-ligne') return 'node-offline'
  if (value === 'echec-etat-noeud') return 'node-status-failure'
  return 'nominal'
}

/**
 * Simulates a decision published by the Governance / Ethics Authority, for the
 * decision demo scenarios. The canonical fixtures keep Cap Azur pending, because
 * the demo approves it live in the Governance Portal; these scenarios only show
 * what the hospital receives. The Hospital Portal never makes a decision. Pure.
 */
export function withSimulatedDecision(
  organization: Organization,
  application: HospitalApplication,
  outcome: GovernanceDecision['outcome'],
): { organization: Organization; application: HospitalApplication; decision: GovernanceDecision } {
  const decidedAt = '2026-10-10T10:30:00+01:00'
  const decision: GovernanceDecision = {
    id: `dec-demo-${application.id}`,
    subjectType: 'hospital_application',
    subjectId: application.id,
    outcome,
    decidedById: 'usr-olfa',
    decidedAt,
    rationale:
      outcome === 'approved'
        ? 'Dossier conforme à la charte de gouvernance fédérée ; une pièce administrative reste à fournir.'
        : "Le dossier ne permet pas d'établir l'autorisation d'exercice de l'établissement.",
    conditions: outcome === 'approved' ? ["Fournir l'attestation d'assurance avant la mise en service du Hospital Node."] : [],
    validUntil: null,
    simulated: true,
  }
  return {
    organization: {
      ...organization,
      governanceStatus: outcome,
      approvalDecisionId: outcome === 'approved' ? decision.id : null,
    },
    application: {
      ...application,
      status: outcome,
      decisionId: decision.id,
      reviewSteps: application.reviewSteps.map((s) =>
        s.step === 'human_review' ? { ...s, status: 'completed', completedAt: decidedAt } : s,
      ),
    },
    decision,
  }
}

/**
 * Simulates the Node summary an installed Hospital Node would report, for the
 * Node status demo scenarios (HC-063). The canonical fixtures have no Node for
 * Cap Azur. Values are fictional and fixed; nothing contacts a Node. Pure.
 */
export function withSimulatedNode(organization: Organization, status: NodeSummary['status']): Organization {
  const reported: Record<NodeSummary['status'], Omit<NodeSummary, 'id' | 'status' | 'simulated'>> = {
    online: { version: '0.4.0', lastSyncAt: '2026-10-10T17:40:00+01:00', dmiState: 'connected' },
    degraded: { version: '0.2.0', lastSyncAt: '2026-10-10T09:15:00+01:00', dmiState: 'disconnected' },
    offline: { version: '0.4.0', lastSyncAt: '2026-10-09T22:05:00+01:00', dmiState: 'connected' },
  }
  return { ...organization, node: { id: nodeRefFor(organization.id), status, ...reported[status], simulated: true } }
}

const SIMULATED_NODE_STATES: Partial<Record<DemoScenario, NodeSummary['status']>> = {
  'node-online': 'online',
  'node-degraded': 'degraded',
  'node-offline': 'offline',
  'node-status-failure': 'online',
}

export interface LoadOptions {
  scenario?: DemoScenario
  /** Simulated network latency in milliseconds. */
  delayMs?: number
}

export async function loadOnboardingSnapshot(
  organizationId: string,
  managerId: string,
  { scenario = 'nominal', delayMs = 400 }: LoadOptions = {},
): Promise<OnboardingSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))

  if (scenario === 'error') {
    throw new Error("Le service d'adhésion simulé est indisponible (scénario de démonstration).")
  }
  const organization = organizations.find((o) => o.id === organizationId)
  const manager = staff.find((p) => p.id === managerId && p.organizationId === organizationId)
  if (!organization || !manager) {
    throw new Error(`Établissement ou responsable inconnu : ${organizationId} / ${managerId}.`)
  }

  const loaded =
    scenario === 'empty' ||
    scenario === 'registration-failure' ||
    scenario === 'profile-failure' ||
    scenario === 'agreement-failure' ||
    scenario === 'technical-failure' ||
    scenario === 'dmi-failure' ||
    scenario === 'submission-failure'
      ? null
      : (applications.find((a) => a.organizationId === organizationId) ?? null)

  let decided = {
    organization,
    application: loaded,
    decision: decisions.find((d) => d.id === loaded?.decisionId) ?? null,
  }
  const simulatedNode = SIMULATED_NODE_STATES[scenario]
  if (
    loaded &&
    (scenario === 'decision-approved' ||
      scenario === 'download-failure' ||
      scenario === 'decision-rejected' ||
      simulatedNode)
  ) {
    decided = withSimulatedDecision(organization, loaded, scenario === 'decision-rejected' ? 'rejected' : 'approved')
  }
  if (simulatedNode) {
    decided = { ...decided, organization: withSimulatedNode(decided.organization, simulatedNode) }
  }
  const { application } = decided

  return {
    organization: decided.organization,
    manager,
    application,
    decision: decided.decision,
    steps: deriveSteps(decided.organization, application),
    notifications: notifications
      .filter((n) => n.recipientId === managerId && (application !== null || n.relatedId === null))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
  }
}
