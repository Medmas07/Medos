import { describe, expect, it } from 'vitest'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  deriveSteps,
  loadOnboardingSnapshot,
  scenarioFromSearch,
  STEP_DEFINITIONS,
} from '../src/services/onboardingService'
import type { OnboardingStep } from '../src/types/onboarding'

const load = (scenario?: 'nominal' | 'empty' | 'error') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

const byId = (steps: OnboardingStep[], id: string) => steps.find((s) => s.id === id)

describe('Hospital Portal onboarding service (MOCKED, canonical fixtures)', () => {
  it('loads the fictional Cap Azur application in human review', async () => {
    const snapshot = await load()
    expect(snapshot.organization.name).toBe('Centre Hospitalier Cap Azur')
    expect(snapshot.manager.lastName).toBe('Sassi')
    expect(snapshot.application?.id).toBe('app-hospital-c')
    expect(snapshot.application?.status).toBe('human_review')
    expect(snapshot.notifications.map((n) => n.id)).toContain('notif-008')
  })

  it('derives one state per portal page, in workflow order', async () => {
    const { steps } = await load()
    expect(steps.map((s) => s.ticket)).toEqual(STEP_DEFINITIONS.map((d) => d.ticket))

    expect(byId(steps, 'registration')?.status).toBe('completed')
    expect(byId(steps, 'documents')).toMatchObject({ status: 'attention', detail: '1 document à fournir.' })
    expect(byId(steps, 'agreements')?.status).toBe('completed')
    expect(byId(steps, 'automated-review')?.status).toBe('attention')
    expect(byId(steps, 'human-review')?.status).toBe('in_progress')
  })

  it('never shows a decision or a Node package before Governance approves', async () => {
    const { steps } = await load()
    expect(byId(steps, 'decision')?.status).toBe('pending')
    for (const step of steps.filter((s) => s.id.startsWith('node-'))) {
      expect(step.status).toBe('locked')
    }
  })

  it('opens the Node pages for an approved organization', async () => {
    const snapshot = await loadOnboardingSnapshot('org-hospital-c', 'usr-mehdi', { delayMs: 0 })
    const approved = deriveSteps(
      { ...snapshot.organization, node: { id: 'node-x', status: 'degraded', version: '0.1.0', lastSyncAt: '2026-10-10T08:00:00+01:00', dmiState: 'disconnected' } },
      { ...snapshot.application!, status: 'approved' },
    )
    expect(byId(approved, 'decision')?.status).toBe('completed')
    expect(byId(approved, 'node-download')?.status).toBe('completed')
    expect(byId(approved, 'node-status')?.status).toBe('attention')
  })

  it('supports explicit empty and error demo scenarios', async () => {
    const empty = await load('empty')
    expect(empty.application).toBeNull()
    expect(empty.notifications).toEqual([])
    expect(byId(empty.steps, 'registration')?.status).toBe('pending')

    await expect(load('error')).rejects.toThrow('indisponible')
    await expect(
      loadOnboardingSnapshot('org-hospital-c', 'usr-olfa', { delayMs: 0 }),
    ).rejects.toThrow('inconnu')
  })

  it('maps the demo query parameter to a scenario', () => {
    expect(scenarioFromSearch('')).toBe('nominal')
    expect(scenarioFromSearch('?demo=vide')).toBe('empty')
    expect(scenarioFromSearch('?demo=erreur')).toBe('error')
  })
})
