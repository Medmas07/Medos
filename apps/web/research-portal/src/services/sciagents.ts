import type {
  ProjectSummary,
  ResearchSnapshot,
  SciAgentsCitation,
  SciAgentsFinding,
  SciAgentsHypothesis,
  SciAgentsInvestigation,
  SciAgentsResult,
} from '../types/research'

/**
 * SciAgents research panel (HC-102), MOCKED. SciAgents is an existing external
 * system reached through the HC-170 contract; this portal neither reimplements
 * nor, at D1, contacts it. These pure functions join each fixture
 * investigation to its project and local controlled-result context, and resolve
 * every claim to its evidence, contradictions, and citations. HC-170 v1.1 sends
 * only two non-identifying concepts upstream. Its output is a research lead: it
 * never becomes clinical data.
 */

export interface ResolvedFinding {
  finding: SciAgentsFinding
  citations: SciAgentsCitation[]
}

export interface ResolvedHypothesis {
  hypothesis: SciAgentsHypothesis
  evidence: ResolvedFinding[]
  contradictions: ResolvedFinding[]
}

export interface ContextEntry {
  controlledResultId: string
  summary: string
  /** Whether it is one of the researcher's controlled results that passed its disclosure check; only those may be sent. */
  released: boolean
}

export interface InvestigationEntry {
  investigation: SciAgentsInvestigation
  summary: ProjectSummary
  context: ContextEntry[]
  /** References of the result that resolve to nothing in it. Any one withholds the whole result. */
  unresolved: string[]
  /** The resolved claims; null unless the investigation completed with every reference resolved. */
  hypotheses: ResolvedHypothesis[] | null
}

/**
 * References of a result that do not resolve within it, as the HC-170 contract
 * requires: hypotheses to evidence and contradictions, those to citations. Pure.
 */
export function unresolvedReferences(result: SciAgentsResult): string[] {
  const ids = (items: { id: string }[]) => new Set(items.map((i) => i.id))
  const evidence = ids(result.evidence)
  const contradictions = ids(result.contradictions)
  const citations = ids(result.citations)
  const missing = [
    ...result.hypotheses.flatMap((h) => [
      ...h.evidenceIds.filter((id) => !evidence.has(id)),
      ...h.contradictionIds.filter((id) => !contradictions.has(id)),
    ]),
    ...[...result.evidence, ...result.contradictions].flatMap((f) => f.citationIds.filter((id) => !citations.has(id))),
  ]
  return [...new Set(missing)]
}

function resolve(result: SciAgentsResult): ResolvedHypothesis[] {
  const finding = (items: SciAgentsFinding[]) => (id: string) => {
    const found = items.find((f) => f.id === id)!
    return { finding: found, citations: found.citationIds.map((c) => result.citations.find((x) => x.id === c)!) }
  }
  return result.hypotheses.map((hypothesis) => ({
    hypothesis,
    evidence: hypothesis.evidenceIds.map(finding(result.evidence)),
    contradictions: hypothesis.contradictionIds.map(finding(result.contradictions)),
  }))
}

/** The researcher's investigations, most recently updated first. Pure. */
export function sciAgentsOverview(snapshot: ResearchSnapshot): InvestigationEntry[] {
  const released = new Set(snapshot.results.filter((r) => r.disclosureCheck === 'passed').map((r) => r.id))
  const entries: InvestigationEntry[] = []
  for (const investigation of snapshot.investigations) {
    const summary = snapshot.projects.find((s) => s.project.id === investigation.projectId)
    if (!summary) continue
    const unresolved = investigation.result ? unresolvedReferences(investigation.result) : []
    entries.push({
      investigation,
      summary,
      context: investigation.controlledResultContext.map((c) => ({ ...c, released: released.has(c.controlledResultId) })),
      unresolved,
      hypotheses:
        investigation.status === 'completed' && investigation.result && unresolved.length === 0
          ? resolve(investigation.result)
          : null,
    })
  }
  return entries.sort((a, b) => b.investigation.updatedAt.localeCompare(a.investigation.updatedAt))
}

/**
 * The `InvestigationRequest` body of the HC-170 contract this investigation
 * corresponds to: the display question, opaque references, and exactly two
 * non-identifying concepts. The local controlled-result context is never added.
 * Nothing sends this request at D1 (HC-172). Pure.
 */
export function investigationRequest(entry: InvestigationEntry): Record<string, unknown> {
  const { investigation } = entry
  return {
    project_ref: investigation.projectId,
    requested_by: investigation.requestedById,
    question: investigation.question,
    ...(investigation.language ? { language: investigation.language } : {}),
    concepts: investigation.concepts,
  }
}
