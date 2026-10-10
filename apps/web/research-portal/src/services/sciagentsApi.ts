import type { SciAgentsInvestigation } from '../types/research'

const configuredBaseUrl = (import.meta.env.VITE_SCIAGENTS_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export const sciAgentsIntegrationConfigured = configuredBaseUrl.length > 0

export interface SubmitInvestigation {
  project_ref: string
  requested_by: string
  question: string
  language?: string
  concepts: [{ label: string }, { label: string }]
}

interface ApiFinding {
  evidence_id?: string
  contradiction_id?: string
  summary: string
  citation_ids: string[]
}

interface ApiInvestigation {
  investigation_id: string
  project_ref: string
  requested_by: string
  question: string
  concepts: { label: string }[]
  status: SciAgentsInvestigation['status']
  created_at: string
  updated_at: string
  clinical_use: 'not_for_clinical_decisions'
  result: null | {
    outcome: 'findings' | 'empty'
    hypotheses: {
      hypothesis_id: string
      statement: string
      confidence: 'low' | 'moderate' | 'high' | null
      evidence_ids: string[]
      contradiction_ids: string[]
    }[]
    evidence: ApiFinding[]
    contradictions: ApiFinding[]
    citations: {
      citation_id: string
      kind: 'publication' | 'controlled_result' | 'other'
      title: string
      source: string
      identifier: string | null
      url: string | null
    }[]
  }
  error: SciAgentsInvestigation['error']
  provenance: {
    provider: { name: 'SciAgents'; version: string | null }
    adapter: { name: string; version: string }
    mocked: boolean
    upstream_request_ref: string | null
  }
}

export class SciAgentsApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.status = status
  }
}

function map(document: ApiInvestigation): SciAgentsInvestigation {
  return {
    id: document.investigation_id,
    projectId: document.project_ref,
    requestedById: document.requested_by,
    question: document.question,
    language: null,
    concepts: document.concepts,
    controlledResultContext: [],
    status: document.status,
    createdAt: document.created_at,
    updatedAt: document.updated_at,
    clinicalUse: document.clinical_use,
    result: document.result && {
      outcome: document.result.outcome,
      hypotheses: document.result.hypotheses.map((item) => ({
        id: item.hypothesis_id,
        statement: item.statement,
        confidence: item.confidence,
        evidenceIds: item.evidence_ids,
        contradictionIds: item.contradiction_ids,
      })),
      evidence: document.result.evidence.map((item) => ({
        id: item.evidence_id!,
        summary: item.summary,
        citationIds: item.citation_ids,
      })),
      contradictions: document.result.contradictions.map((item) => ({
        id: item.contradiction_id!,
        summary: item.summary,
        citationIds: item.citation_ids,
      })),
      citations: document.result.citations.map((item) => ({
        id: item.citation_id,
        kind: item.kind,
        title: item.title,
        source: item.source,
        controlledResultId: item.kind === 'controlled_result' ? item.identifier : null,
        url: item.url,
      })),
    },
    error: document.error,
    provenance: {
      provider: document.provenance.provider,
      adapter: document.provenance.adapter,
      mocked: document.provenance.mocked,
      upstreamRequestRef: document.provenance.upstream_request_ref,
      note: 'Résultat reçu par l’intégration serveur HC-172. Usage de recherche uniquement.',
    },
  }
}

export function createSciAgentsApi(baseUrl: string, fetcher: typeof fetch = fetch) {
  const normalizedBaseUrl = baseUrl.replace(/\/$/, '')
  const request = async (path: string, init?: RequestInit): Promise<SciAgentsInvestigation> => {
    if (!normalizedBaseUrl) throw new SciAgentsApiError('L’intégration SciAgents n’est pas configurée.', null)
    let response: Response
    try {
      response = await fetcher(`${normalizedBaseUrl}${path}`, init)
    } catch {
      throw new SciAgentsApiError('Le service d’intégration SciAgents est indisponible.', null)
    }
    if (!response.ok) {
      const problem = (await response.json().catch(() => ({}))) as { detail?: string; title?: string }
      throw new SciAgentsApiError(problem.detail ?? problem.title ?? 'La requête SciAgents a échoué.', response.status)
    }
    return map((await response.json()) as ApiInvestigation)
  }
  return {
    submit: (input: SubmitInvestigation) => request('/v1/investigations', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),
    get: (id: string) => request(`/v1/investigations/${encodeURIComponent(id)}`),
  }
}

const configuredApi = createSciAgentsApi(configuredBaseUrl)
export const submitInvestigation = configuredApi.submit
export const getInvestigation = configuredApi.get
