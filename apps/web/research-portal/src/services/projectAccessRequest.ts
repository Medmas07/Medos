import type { PageId, ProjectSummary, ResearchAccessRequest, ResearchSnapshot } from '../types/research'
import { editableDraft } from './projectCreation'
import { isSelectable, selectedHospitals } from './projectHospitals'
import { populationStatus } from './projectPopulation'
import { variablesStatus } from './projectVariables'
import { derivePages, FIXTURE_ACCESS_REQUESTS } from './researchService'

/**
 * Research data-access request submission (HC-097), MOCKED. Submitting turns a
 * complete draft into a request under review, in the portal's session state
 * only, after a simulated delay: no Governance Node research API exists yet
 * (HC-133 is PLANNED), so the Governance / Ethics Authority does not receive
 * it. Submitting authorizes nothing and unlocks no Compute-to-Data page; once
 * submitted, the project can no longer be edited.
 */

export type ReadinessCheckId = 'protocol' | 'population' | 'variables' | 'hospitals'

export interface ReadinessCheck {
  id: ReadinessCheckId
  label: string
  ready: boolean
  /** French explanation of what is present or missing. */
  detail: string
  /** The page that completes this part of the project. */
  page: PageId
}

/**
 * What the Governance review needs before it can decide, the checks HC-078
 * applies, in the order of the workflow. Pure.
 */
export function readinessChecks({ project }: Pick<ProjectSummary, 'project'>): ReadinessCheck[] {
  const hospitals = selectedHospitals(project.participatingOrganizationIds).filter(isSelectable)
  const variables = project.variableNames?.length ?? 0
  return [
    {
      id: 'protocol',
      label: 'Protocole de recherche',
      ready: project.protocolDocument !== null,
      detail: project.protocolDocument ? `${project.protocolDocument.title} déposé.` : 'Aucun protocole déposé.',
      page: 'protocol',
    },
    {
      id: 'population',
      label: 'Population étudiée',
      ready: populationStatus(project) === 'defined',
      detail:
        populationStatus(project) === 'defined'
          ? "Description et critères d'éligibilité définis."
          : 'La description et au moins un critère structuré sont requis.',
      page: 'population',
    },
    {
      id: 'variables',
      label: 'Variables demandées',
      ready: variablesStatus(project) === 'justified',
      detail:
        variablesStatus(project) === 'justified'
          ? `${variables} variable(s) justifiée(s).`
          : 'Au moins une variable du catalogue et sa justification sont requises.',
      page: 'variables',
    },
    {
      id: 'hospitals',
      label: 'Établissements participants',
      ready: hospitals.length > 0,
      detail:
        hospitals.length > 0
          ? `${hospitals.map((o) => o.shortName).join(', ')}.`
          : 'Au moins un établissement avec un Hospital Node approuvé est requis.',
      page: 'hospitals',
    },
  ]
}

export const isReady = (summary: Pick<ProjectSummary, 'project'>) => readinessChecks(summary).every((c) => c.ready)

/** The form's values. */
export interface SubmissionDraft {
  /** The researcher acknowledges that the request authorizes nothing by itself and returns no raw data. */
  acknowledged: boolean
}

export type SubmissionErrors = Partial<Record<'checks' | keyof SubmissionDraft, string>>

/** Validates a submission for this project. Pure; returns French messages. */
export function validateSubmission(summary: Pick<ProjectSummary, 'project'>, draft: SubmissionDraft): SubmissionErrors {
  const errors: SubmissionErrors = {}
  const missing = readinessChecks(summary).filter((c) => !c.ready)
  if (missing.length > 0) errors.checks = `Complétez d'abord : ${missing.map((c) => c.label.toLowerCase()).join(', ')}.`
  if (!draft.acknowledged) errors.acknowledged = 'Confirmez avoir pris connaissance des conditions de la demande.'
  return errors
}

/** Next fictional request identifier after the existing `rar-NNN` ones. Pure. */
export function nextRequestId(existing: readonly Pick<ResearchAccessRequest, 'id'>[]): string {
  const highest = existing.reduce((max, r) => Math.max(max, Number(/^rar-(\d+)$/.exec(r.id)?.[1] ?? 0)), 0)
  return `rar-${String(highest + 1).padStart(3, '0')}`
}

export interface SubmitOptions {
  /** Simulated network latency in milliseconds. */
  delayMs?: number
  /** Submission time of the request. */
  now?: Date
}

export interface SubmittedRequest {
  request: ResearchAccessRequest
  /** The snapshot with the project under review and page availability re-derived. */
  snapshot: ResearchSnapshot
}

/**
 * Submits a complete draft's access request, after a simulated delay. The
 * request is under review, without a decision: only the Governance / Ethics
 * Authority can decide. Rejects an incomplete project, a missing
 * acknowledgement, or a project already submitted.
 */
export async function submitAccessRequest(
  snapshot: ResearchSnapshot,
  projectId: string,
  draft: SubmissionDraft,
  { delayMs = 400, now = new Date() }: SubmitOptions = {},
): Promise<SubmittedRequest> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  const summary = editableDraft(snapshot, projectId)
  if (Object.keys(validateSubmission(summary, draft)).length > 0) {
    throw new Error('La demande est incomplète : corrigez les points signalés.')
  }

  const request: ResearchAccessRequest = {
    // Fixture identifiers stay reserved even when the demo hides them (`?demo=vide`).
    id: nextRequestId([...FIXTURE_ACCESS_REQUESTS, ...snapshot.projects.flatMap((s) => (s.request ? [s.request] : []))]),
    projectId,
    submittedById: snapshot.researcher.id,
    submittedAt: now.toISOString(),
    status: 'under_review',
    decisionId: null,
  }
  const projects = snapshot.projects.map((s) =>
    s.project.id === projectId
      ? {
          ...s,
          project: { ...s.project, status: 'under_review' as const, researchAccessRequestId: request.id },
          request,
          decision: null,
          authorized: false,
        }
      : s,
  )
  return { request, snapshot: { ...snapshot, projects, pages: derivePages(projects, new Date(snapshot.asOf)) } }
}
