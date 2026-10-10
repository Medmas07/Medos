import { describe, expect, it, vi } from 'vitest'
import { createSciAgentsApi } from '../src/services/sciagentsApi'

const response = {
  investigation_id: '0b6f5a1e-3c2d-4e7f-9a8b-1c2d3e4f5a6b',
  project_ref: 'proj-001',
  requested_by: 'usr-aymen',
  question: 'Question fictive.',
  concepts: [{ label: 'Metformin' }, { label: 'Diabetes' }],
  status: 'completed',
  created_at: '2026-10-10T11:00:00Z',
  updated_at: '2026-10-10T11:01:00Z',
  clinical_use: 'not_for_clinical_decisions',
  result: { outcome: 'empty', hypotheses: [], evidence: [], contradictions: [], citations: [] },
  error: null,
  provenance: {
    provider: { name: 'SciAgents', version: null },
    adapter: { name: 'hackcure-sciagents-adapter', version: '0.1.0' },
    mocked: false,
    upstream_request_ref: 'run-1',
  },
}

describe('SciAgents HTTP client (HC-172)', () => {
  it('submits only the HC-170 request and maps the response', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 202 }))
    const api = createSciAgentsApi('https://integration.invalid', fetch)
    const input = {
      project_ref: 'proj-001',
      requested_by: 'usr-aymen',
      question: 'Question fictive.',
      concepts: [{ label: 'Metformin' }, { label: 'Diabetes' }] as [{ label: string }, { label: string }],
    }
    const result = await api.submit(input)
    expect(result).toMatchObject({ id: response.investigation_id, status: 'completed', result: { outcome: 'empty' } })
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input)
  })

  it('maps a failed HTTP response to an explicit error', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'SciAgents indisponible.' }), { status: 503 }))
    const api = createSciAgentsApi('https://integration.invalid', fetch)
    await expect(api.get('known')).rejects.toMatchObject({ message: 'SciAgents indisponible.', status: 503 })
  })
})
