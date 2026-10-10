import { describe, expect, it } from 'vitest'
import { investigationProgressDisplay } from '../src/services/sciagentsProgress'
import type { SciAgentsInvestigation } from '../src/types/research'

const progress = (status: SciAgentsInvestigation['status'], percent: number | null = null) =>
  investigationProgressDisplay({
    status,
    progress: status === 'queued' ? null : { stageLabel: 'Evidence grounding', percent, updatedAt: '2026-10-10T11:00:00Z' },
  })

describe('SciAgents execution progress (HC-173)', () => {
  it('keeps queued and unknown-duration running work explicit without inventing a percentage', () => {
    expect(progress('queued')).toMatchObject({ label: 'En attente de SciAgents', percent: null, tone: 'neutral' })
    expect(progress('running')).toMatchObject({ label: 'Evidence grounding', percent: null, tone: 'info' })
    expect(progress('running').detail).toContain('aucune estimation')
  })

  it('shows an adapter estimate when one exists', () => {
    expect(progress('running', 45)).toMatchObject({ percent: 45, tone: 'info' })
    expect(progress('running', 45).detail).toContain('45 %')
  })

  it('makes completed and failed terminal states unambiguous', () => {
    expect(progress('completed')).toMatchObject({ percent: 100, tone: 'success' })
    expect(progress('failed', 70)).toMatchObject({ percent: null, tone: 'danger' })
  })
})
