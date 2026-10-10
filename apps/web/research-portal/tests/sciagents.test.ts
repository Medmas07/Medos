import { describe, expect, it } from 'vitest'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot, scenarioFromSearch, type DemoScenario } from '../src/services/researchService'
import { investigationRequest, sciAgentsOverview, unresolvedReferences } from '../src/services/sciagents'
import type { ResearchSnapshot, SciAgentsResult } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const load = (scenario: DemoScenario = 'nominal', now = NOW) =>
  loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now, scenario })

/** The fixture investigation's result, changed by `mutate`. */
function withResult(snapshot: ResearchSnapshot, mutate: (result: SciAgentsResult) => SciAgentsResult): ResearchSnapshot {
  return {
    ...snapshot,
    investigations: snapshot.investigations.map((i) => ({ ...i, result: i.result && mutate(i.result) })),
  }
}

describe('SciAgents research panel (HC-102, MOCKED)', () => {
  it('shows the fixture investigation as a mocked, research-only result from the external SciAgents', async () => {
    const [entry, ...others] = sciAgentsOverview(await load())
    expect(others).toEqual([])
    expect(entry.investigation).toMatchObject({
      id: 'inv-001',
      status: 'completed',
      clinicalUse: 'not_for_clinical_decisions',
      error: null,
      provenance: { provider: { name: 'SciAgents', version: null }, mocked: true, upstreamRequestRef: null },
    })
    expect(entry.investigation.provenance.note).toContain('HC-171')
    expect(entry.summary.project.id).toBe('proj-001')
    expect(entry.unresolved).toEqual([])
  })

  it('resolves each hypothesis to its confidence, evidence, contradictions, and citations', async () => {
    const [entry] = sciAgentsOverview(await load())
    expect(
      entry.hypotheses?.map((h) => ({
        id: h.hypothesis.id,
        confidence: h.hypothesis.confidence,
        evidence: h.evidence.map((e) => [e.finding.id, e.citations.map((c) => c.id)]),
        contradictions: h.contradictions.map((x) => [x.finding.id, x.citations.map((c) => c.id)]),
      })),
    ).toEqual([
      { id: 'inv-001-h1', confidence: 'moderate', evidence: [['inv-001-e2', ['inv-001-c2']]], contradictions: [] },
      {
        id: 'inv-001-h2',
        confidence: 'low',
        evidence: [['inv-001-e1', ['inv-001-c1']]],
        contradictions: [['inv-001-x1', ['inv-001-c1']]],
      },
    ])
    const citations = entry.investigation.result!.citations
    expect(citations.map((c) => [c.kind, c.controlledResultId])).toEqual([
      ['controlled_result', 'res-001'],
      ['publication', null],
    ])
  })

  it('builds a request with only workflow metadata and two non-identifying concepts', async () => {
    const [entry] = sciAgentsOverview(await load())
    expect(entry.context.map((c) => [c.controlledResultId, c.released])).toEqual([['res-001', true]])
    const request = investigationRequest(entry)
    expect(Object.keys(request).sort()).toEqual(['concepts', 'language', 'project_ref', 'question', 'requested_by'])
    expect(request).toMatchObject({ project_ref: 'proj-001', requested_by: 'usr-aymen', language: 'fr' })
    expect(request.concepts).toEqual([{ label: 'Metformin' }, { label: 'Diabetes' }])
    expect(request).not.toHaveProperty('controlled_results')
  })

  it('keeps controlled-result context local even when its disclosure check passed', async () => {
    const snapshot = await load()
    const [entry] = sciAgentsOverview(snapshot)
    expect(entry.context[0].released).toBe(true)
    expect(investigationRequest(entry)).not.toHaveProperty('controlled_results')
  })

  it('withholds a result whose references do not resolve', async () => {
    const broken = withResult(await load(), (r) => ({ ...r, citations: r.citations.slice(0, 1) }))
    const [entry] = sciAgentsOverview(broken)
    expect(entry.unresolved).toEqual(['inv-001-c2'])
    expect(entry.hypotheses).toBeNull()

    const result = (await load()).investigations[0].result!
    expect(unresolvedReferences(result)).toEqual([])
    expect(
      unresolvedReferences({ ...result, hypotheses: [{ ...result.hypotheses[0], evidenceIds: ['inv-001-x1'] }] }),
    ).toEqual(['inv-001-x1'])
  })

  it('shows a SciAgents timeout as a failed investigation without hypotheses', async () => {
    expect(scenarioFromSearch('?demo=echec-sciagents')).toBe('sciagents-failure')
    const [entry] = sciAgentsOverview(await load('sciagents-failure'))
    expect(entry.investigation).toMatchObject({ status: 'failed', result: null, error: { code: 'timeout', retryable: true } })
    expect(entry.hypotheses).toBeNull()
  })

  it('shows nothing in the empty scenario and stays available once the authorization has expired', async () => {
    expect(sciAgentsOverview(await load('empty'))).toEqual([])
    const later = await load('nominal', new Date('2030-01-01T00:00:00Z'))
    expect(later.pages.find((p) => p.id === 'sciagents')?.status).toBe('available')
    expect(sciAgentsOverview(later).map((e) => e.investigation.id)).toEqual(['inv-001'])
  })
})
