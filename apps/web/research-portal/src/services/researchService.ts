import governanceFixtures from '../../../../../demo-data/governance.json'
import notificationFixtures from '../../../../../demo-data/notifications.json'
import organizationFixtures from '../../../../../demo-data/organizations.json'
import peopleFixtures from '../../../../../demo-data/people.json'
import researchFixtures from '../../../../../demo-data/research.json'
import type {
  ComputeJob,
  ControlledResultSummary,
  GovernanceDecision,
  Organization,
  PageId,
  PortalNotification,
  PortalPage,
  ProjectSummary,
  ResearchAccessRequest,
  ResearchProject,
  ResearchSnapshot,
  StaffMember,
} from '../types/research'

/**
 * MOCKED research service. It reads the canonical fictional fixtures in the
 * browser and simulates latency; there is no Research Service API yet. The
 * portal only displays Governance decisions: nothing here can authorize a
 * request, run code, or reach a Hospital Node.
 */

const projects = researchFixtures.projects as unknown as ResearchProject[]
const notebooks = researchFixtures.notebooks as unknown as { id: string; projectId: string }[]
const jobs = researchFixtures.computeJobs as unknown as ComputeJob[]
const results = researchFixtures.controlledResults as unknown as ControlledResultSummary[]
const investigations = researchFixtures.sciAgentsInvestigations as unknown as { id: string; projectId: string }[]
const requests = governanceFixtures.researchAccessRequests as unknown as ResearchAccessRequest[]
const decisions = governanceFixtures.decisions as unknown as GovernanceDecision[]
const organizations = organizationFixtures.organizations as unknown as Organization[]
const staff = peopleFixtures.staff as unknown as StaffMember[]
const notifications = notificationFixtures.notifications as unknown as PortalNotification[]

/** Every fixture project; a new project's identifier must not reuse one of theirs. */
export const FIXTURE_PROJECTS: readonly ResearchProject[] = projects

/** Every fixture access request; a new request's identifier must not reuse one of theirs. */
export const FIXTURE_ACCESS_REQUESTS: readonly ResearchAccessRequest[] = requests

/** Organizations whose Hospital Node could take part in a study: hospitals and private practices. */
export const HEALTHCARE_ORGANIZATIONS: readonly Organization[] = organizations.filter(
  (o) => o.type === 'hospital' || o.type === 'private_practice',
)

/** The known organizations among these identifiers, in the same order. Pure. */
export function organizationsByIds(ids: readonly string[]): Organization[] {
  return ids.map((id) => organizations.find((o) => o.id === id)).filter((o): o is Organization => o !== undefined)
}

/** Demo persona: the fictional principal investigator of the cardiometabolic research lab. */
export const DEMO_RESEARCHER_ID = 'usr-aymen'

export type PageSection = 'projects' | 'compute' | 'sciagents'

export interface PageDefinition {
  id: PageId
  label: string
  ticket: string
  section: PageSection
}

/** Portal pages in the order of the product vision's research workflow. */
export const PAGE_DEFINITIONS: readonly PageDefinition[] = [
  { id: 'dashboard', label: 'Tableau de bord', ticket: 'HC-091', section: 'projects' },
  { id: 'new-project', label: 'Nouveau projet', ticket: 'HC-092', section: 'projects' },
  { id: 'protocol', label: 'Protocole et documents', ticket: 'HC-093', section: 'projects' },
  { id: 'population', label: 'Population étudiée', ticket: 'HC-094', section: 'projects' },
  { id: 'variables', label: 'Variables demandées', ticket: 'HC-095', section: 'projects' },
  { id: 'hospitals', label: 'Établissements participants', ticket: 'HC-096', section: 'projects' },
  { id: 'submit-request', label: "Demande d'accès", ticket: 'HC-097', section: 'projects' },
  { id: 'request-status', label: 'Suivi des demandes', ticket: 'HC-098', section: 'projects' },
  { id: 'workspace', label: 'Espace de travail', ticket: 'HC-099', section: 'compute' },
  { id: 'execution', label: 'Exécutions', ticket: 'HC-100', section: 'compute' },
  { id: 'results', label: 'Résultats contrôlés', ticket: 'HC-101', section: 'compute' },
  { id: 'sciagents', label: 'SciAgents', ticket: 'HC-102', section: 'sciagents' },
]

const LOCKED_DETAIL = "Disponible après autorisation d'une demande par l'Autorité de gouvernance."

function plural(count: number, word: string): string {
  return `${count} ${word}${count > 1 ? 's' : ''}`
}

/**
 * Whether a project may use Compute-to-Data: its access request is approved by a
 * Governance decision that is still valid at `now`.
 */
export function isAuthorized(summary: Pick<ProjectSummary, 'request' | 'decision'>, now: Date): boolean {
  const { request, decision } = summary
  return (
    request?.status === 'approved' &&
    decision?.outcome === 'approved' &&
    (decision.validUntil === null || new Date(decision.validUntil) > now)
  )
}

/** Derives the availability of every portal page from fixture data. Pure. */
export function derivePages(summaries: ProjectSummary[], now: Date): PortalPage[] {
  const projectIds = new Set(summaries.map((s) => s.project.id))
  const ownJobs = jobs.filter((j) => projectIds.has(j.projectId))
  const ownJobIds = new Set(ownJobs.map((j) => j.id))
  const submitted = summaries.filter((s) => s.request !== null)
  const approved = submitted.filter((s) => s.request?.status === 'approved').length
  const underReview = submitted.filter((s) => s.request?.status === 'under_review').length
  const authorized = summaries.some((s) => isAuthorized(s, now))

  const details: Record<PageId, string> = {
    dashboard: `${plural(summaries.length, 'projet')} de recherche.`,
    'new-project': "Création d'un projet de recherche.",
    protocol: `${plural(summaries.filter((s) => s.project.protocolDocument).length, 'protocole')} déposé(s).`,
    population: `${plural(summaries.filter((s) => s.project.population.trim()).length, 'population')} décrite(s).`,
    variables: `${plural(summaries.reduce((n, s) => n + s.project.variables.length, 0), 'variable')} demandée(s).`,
    hospitals: `${plural(new Set(summaries.flatMap((s) => s.project.participatingOrganizationIds)).size, 'établissement')} sollicité(s).`,
    'submit-request': `${plural(submitted.length, 'demande')} soumise(s) à l'Autorité de gouvernance.`,
    'request-status': `${approved} approuvée(s), ${underReview} en revue.`,
    workspace: `${plural(notebooks.filter((n) => projectIds.has(n.projectId)).length, 'notebook')} fictif(s).`,
    execution: `${plural(ownJobs.length, 'exécution')} simulée(s).`,
    results: `${plural(results.filter((r) => ownJobIds.has(r.jobId)).length, 'résultat')} contrôlé(s).`,
    sciagents: `${plural(investigations.filter((i) => projectIds.has(i.projectId)).length, 'investigation')} fictive(s) (MOCKED).`,
  }

  return PAGE_DEFINITIONS.map((def) => {
    const locked = def.section === 'compute' && !authorized
    return {
      id: def.id,
      label: def.label,
      ticket: def.ticket,
      status: locked ? 'locked' : 'available',
      detail: locked ? LOCKED_DETAIL : details[def.id],
    }
  })
}

function summarize(project: ResearchProject, now: Date): ProjectSummary {
  const request = requests.find((r) => r.id === project.researchAccessRequestId) ?? null
  const decision =
    (request &&
      decisions.find(
        (d) => d.id === request.decisionId && d.subjectType === 'research_access_request' && d.subjectId === request.id,
      )) ??
    null
  const summary = {
    project,
    request,
    decision,
    participatingOrganizations: organizationsByIds(project.participatingOrganizationIds),
  }
  return { ...summary, authorized: isAuthorized(summary, now) }
}

/**
 * Demo scenarios, selected with `?demo=vide`, `?demo=erreur`, or `?demo=echec-depot`
 * (the first document upload of the page load is interrupted) in the URL.
 */
export type DemoScenario = 'nominal' | 'empty' | 'error' | 'upload-failure'

export function scenarioFromSearch(search: string): DemoScenario {
  const value = new URLSearchParams(search).get('demo')
  if (value === 'vide') return 'empty'
  if (value === 'erreur') return 'error'
  if (value === 'echec-depot') return 'upload-failure'
  return 'nominal'
}

export interface LoadOptions {
  scenario?: DemoScenario
  /** Simulated network latency in milliseconds. */
  delayMs?: number
  /** Reference time for decision validity. */
  now?: Date
}

export async function loadResearchSnapshot(
  researcherId: string,
  { scenario = 'nominal', delayMs = 400, now = new Date() }: LoadOptions = {},
): Promise<ResearchSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))

  if (scenario === 'error') {
    throw new Error('Le service de recherche simulé est indisponible (scénario de démonstration).')
  }
  const researcher = staff.find((p) => p.id === researcherId && p.role === 'researcher')
  const organization = organizations.find((o) => o.id === researcher?.organizationId)
  if (!researcher || !organization) {
    throw new Error(`Chercheur ou organisation inconnu : ${researcherId}.`)
  }

  const summaries =
    scenario === 'empty'
      ? []
      : projects
          .filter((p) => p.principalInvestigatorId === researcherId)
          .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
          .map((p) => summarize(p, now))
  const projectIds = new Set(summaries.map((s) => s.project.id))
  const ownJobs = jobs.filter((j) => projectIds.has(j.projectId))
  const ownJobIds = new Set(ownJobs.map((j) => j.id))

  return {
    asOf: now.toISOString(),
    researcher,
    organization,
    projects: summaries,
    jobs: ownJobs,
    // Release metadata only: the aggregate rows stay with the result panel (HC-101).
    results: results
      .filter((r) => ownJobIds.has(r.jobId))
      .map(({ id, jobId, title, minimumCellSize, disclosureCheck, provenance }) => ({
        id,
        jobId,
        title,
        minimumCellSize,
        disclosureCheck,
        provenance,
      })),
    pages: derivePages(summaries, now),
    notifications: notifications
      .filter((n) => n.recipientId === researcherId && (scenario !== 'empty' || n.relatedId === null))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
  }
}
