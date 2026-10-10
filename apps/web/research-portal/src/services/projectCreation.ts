import type { ProjectSummary, ResearchProject, ResearchSnapshot } from '../types/research'
import { derivePages, FIXTURE_PROJECTS } from './researchService'

/**
 * Research project creation (HC-092), MOCKED. A new project is a draft held in
 * the portal's session state only: no Research Service is called, nothing is
 * persisted, and creating a project requests no data access. Protocol,
 * population, variables, and hospitals are completed by HC-093 to HC-096.
 */

export const TITLE_MIN = 10
export const TITLE_MAX = 150
export const SUMMARY_MIN = 30
export const SUMMARY_MAX = 1000

export interface ProjectDraft {
  title: string
  summary: string
}

export type ProjectDraftErrors = Partial<Record<keyof ProjectDraft, string>>

const normalize = (text: string) => text.trim().replace(/\s+/g, ' ')

/** Validates a draft against the researcher's existing projects. Pure; returns French messages. */
export function validateProjectDraft(draft: ProjectDraft, existing: readonly ResearchProject[]): ProjectDraftErrors {
  const errors: ProjectDraftErrors = {}
  const title = normalize(draft.title)
  const summary = normalize(draft.summary)

  if (!title) errors.title = 'Le titre est obligatoire.'
  else if (title.length < TITLE_MIN) errors.title = `Le titre doit compter au moins ${TITLE_MIN} caractères.`
  else if (title.length > TITLE_MAX) errors.title = `Le titre ne doit pas dépasser ${TITLE_MAX} caractères.`
  else if (existing.some((p) => p.title.toLocaleLowerCase('fr') === title.toLocaleLowerCase('fr')))
    errors.title = 'Un de vos projets porte déjà ce titre.'

  if (!summary) errors.summary = "L'objectif scientifique est obligatoire."
  else if (summary.length < SUMMARY_MIN)
    errors.summary = `L'objectif doit compter au moins ${SUMMARY_MIN} caractères.`
  else if (summary.length > SUMMARY_MAX)
    errors.summary = `L'objectif ne doit pas dépasser ${SUMMARY_MAX} caractères.`

  return errors
}

/**
 * A project can be completed (documents, population, ...) only while it is a
 * draft without an access request: once submitted, the Governance / Ethics
 * Authority reviews it as it is.
 */
export function isEditableDraft(summary: Pick<ProjectSummary, 'project' | 'request'>): boolean {
  return summary.project.status === 'draft' && summary.request === null
}

/** The project to open first: the newest editable draft, otherwise the newest project. */
export function defaultDraftId(snapshot: ResearchSnapshot): string | null {
  return (snapshot.projects.find(isEditableDraft) ?? snapshot.projects[0])?.project.id ?? null
}

/** The project's summary if it can still be completed; throws a French message otherwise. */
export function editableDraft(snapshot: ResearchSnapshot, projectId: string): ProjectSummary {
  const summary = snapshot.projects.find((s) => s.project.id === projectId)
  if (!summary) throw new Error(`Projet inconnu : ${projectId}.`)
  if (!isEditableDraft(summary)) {
    throw new Error("La demande d'accès est soumise : le projet ne peut plus être modifié.")
  }
  return summary
}

/** Returns the snapshot with this project replaced and page availability re-derived. Pure. */
export function withProject(snapshot: ResearchSnapshot, project: ResearchProject): ResearchSnapshot {
  const projects = snapshot.projects.map((s) => (s.project.id === project.id ? { ...s, project } : s))
  return { ...snapshot, projects, pages: derivePages(projects, new Date(snapshot.asOf)) }
}

/** Next fictional project identifier after the existing `proj-NNN` ones. Pure. */
export function nextProjectId(existing: readonly ResearchProject[]): string {
  const highest = existing.reduce((max, p) => Math.max(max, Number(/^proj-(\d+)$/.exec(p.id)?.[1] ?? 0)), 0)
  return `proj-${String(highest + 1).padStart(3, '0')}`
}

export interface CreateOptions {
  /** Simulated network latency in milliseconds. */
  delayMs?: number
  /** Creation time of the project. */
  now?: Date
}

export interface CreatedProject {
  project: ResearchProject
  /** The snapshot with the new draft first and page availability re-derived. */
  snapshot: ResearchSnapshot
}

/**
 * Creates a draft project for the signed-in researcher, after a simulated delay.
 * Rejects an invalid draft. The draft has no access request, so it unlocks no
 * Compute-to-Data page.
 */
export async function createResearchProject(
  snapshot: ResearchSnapshot,
  draft: ProjectDraft,
  { delayMs = 400, now = new Date() }: CreateOptions = {},
): Promise<CreatedProject> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))

  const own = snapshot.projects.map((s) => s.project)
  const errors = validateProjectDraft(draft, own)
  if (Object.keys(errors).length > 0) {
    throw new Error('Le projet est incomplet : corrigez les champs signalés.')
  }

  const project: ResearchProject = {
    // Fixture identifiers stay reserved even when the demo hides them (`?demo=vide`),
    // so fixture jobs and results are never attributed to the new draft.
    id: nextProjectId([...FIXTURE_PROJECTS, ...own]),
    title: normalize(draft.title),
    principalInvestigatorId: snapshot.researcher.id,
    organizationId: snapshot.organization.id,
    status: 'draft',
    createdAt: now.toISOString(),
    summary: normalize(draft.summary),
    population: '',
    variables: [],
    participatingOrganizationIds: [],
    protocolDocument: null,
    researchAccessRequestId: null,
  }
  const summary: ProjectSummary = {
    project,
    request: null,
    decision: null,
    participatingOrganizations: [],
    authorized: false,
  }
  const projects = [summary, ...snapshot.projects]

  return {
    project,
    snapshot: { ...snapshot, projects, pages: derivePages(projects, new Date(snapshot.asOf)) },
  }
}
