import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { applyChecklist, installationGuide } from '../src/services/installationService'
import {
  compareVersions,
  LATEST_NODE_VERSION,
  nodeStatus,
  nodeStatusReport,
  refreshNodeStatus,
  type NodeStatusReport,
} from '../src/services/nodeStatusService'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  listOrganizations,
  loadOnboardingSnapshot,
  scenarioFromSearch,
  type DemoScenario,
} from '../src/services/onboardingService'
import type { OnboardingSnapshot } from '../src/types/onboarding'

const now = new Date('2026-10-10T18:00:00+01:00')
const load = (scenario: DemoScenario = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })
const repo = (path: string) => fileURLToPath(new URL(`../../../../${path}`, import.meta.url))

function report(snapshot: OnboardingSnapshot): NodeStatusReport {
  const status = nodeStatus(snapshot)
  if (status.kind !== 'ready') throw new Error(`expected a report, got ${status.kind}`)
  return status.report
}
const states = (r: NodeStatusReport) => Object.fromEntries(r.indicators.map((i) => [i.id, [i.state, i.value]]))

describe('Hospital Node status dashboard', () => {
  it('stays in sync with the version the Hospital Node runtime reports', () => {
    const source = readFileSync(repo('instances/hospital-node/application/get_node_status.py'), 'utf-8')
    expect(source.match(/^NODE_VERSION = "([^"]+)"$/m)?.[1]).toBe(LATEST_NODE_VERSION)
  })

  it('shows nothing before an approval or after a rejection', async () => {
    expect(nodeStatus(await load()).kind).toBe('not_approved')
    expect(nodeStatus(await load('empty')).kind).toBe('not_approved')
    expect(nodeStatus(await load('decision-rejected')).kind).toBe('not_approved')
  })

  it('reports no state for the canonical approved application, which has no installed node', async () => {
    const approved = await load('decision-approved')
    expect(approved.organization.node).toBeNull()
    expect(nodeStatus(approved)).toEqual({ kind: 'not_installed', declaredSteps: 0 })
    // Declaring every installation step is not a verification: still no state received.
    const declared = installationGuide(approved)!.reduce((s, step) => applyChecklist(s, step.id, true), approved)
    expect(nodeStatus(declared)).toEqual({ kind: 'not_installed', declaredSteps: 9 })
  })

  it('shows a coherent online node', async () => {
    const snapshot = await load('node-online')
    const r = report(snapshot)
    expect(r.node).toMatchObject({ id: 'node-hospital-c', simulated: true })
    expect(states(r)).toEqual({
      connectivity: ['ok', 'En ligne'],
      dmi: ['ok', 'Connecté'],
      version: ['ok', LATEST_NODE_VERSION],
      health: ['ok', '4 / 4'],
      synchronization: ['ok', 'À jour'],
    })
    expect(r.indicators.find((i) => i.id === 'synchronization')?.at).toBe(r.node.lastSyncAt)
    expect(snapshot.steps.find((s) => s.id === 'node-status')).toMatchObject({ status: 'completed' })
  })

  it('shows a degraded node with a disconnected DMI Adapter, interrupted sync, and an update', async () => {
    const snapshot = await load('node-degraded')
    const r = report(snapshot)
    expect(states(r)).toEqual({
      connectivity: ['warning', 'Dégradé'],
      dmi: ['critical', 'Déconnecté'],
      version: ['warning', '0.2.0'],
      health: ['warning', '3 / 4'],
      synchronization: ['warning', 'Interrompue'],
    })
    expect(r.healthChecks.find((c) => c.id === 'dmi-adapter')?.state).toBe('critical')
    expect(snapshot.steps.find((s) => s.id === 'node-status')).toMatchObject({ status: 'attention' })
  })

  it('shows last known values as unknown when the node is offline', async () => {
    const r = report(await load('node-offline'))
    expect(states(r)).toEqual({
      connectivity: ['critical', 'Hors ligne'],
      dmi: ['unknown', 'Inconnu'],
      version: ['ok', LATEST_NODE_VERSION],
      health: ['critical', '0 / 4'],
      synchronization: ['unknown', 'Inconnue'],
    })
    expect(r.healthChecks.map((c) => c.state)).toEqual(['critical', 'unknown', 'unknown', 'unknown'])
  })

  it('derives the same states from a fixture node', () => {
    const practice = listOrganizations().find((o) => o.id === 'org-private-practice')!
    const r = nodeStatusReport(practice.node!)
    expect(r.node.simulated).toBeUndefined()
    expect(states(r).connectivity).toEqual(['warning', 'Dégradé'])
    expect(states(r).dmi).toEqual(['critical', 'Déconnecté'])
    expect(states(r).version).toEqual(['warning', '0.1.0'])
  })

  it('carries no clinical data', async () => {
    const text = JSON.stringify(report(await load('node-online')))
    for (const word of ['patient', 'diagnos', 'prescri', 'encounter', 'medication']) {
      expect(text.toLowerCase()).not.toContain(word)
    }
  })

  it('compares versions numerically', () => {
    expect(compareVersions('0.2.0', '0.3.0')).toBeLessThan(0)
    expect(compareVersions('0.10.0', '0.3.0')).toBeGreaterThan(0)
    expect(compareVersions('0.3', '0.3.0')).toBe(0)
  })

  it('refreshes without changing anything, and fails in the failure scenario', async () => {
    expect(scenarioFromSearch('?demo=echec-etat-noeud')).toBe('node-status-failure')
    const snapshot = await load('node-status-failure')
    expect(report(snapshot).node.status).toBe('online')
    await expect(refreshNodeStatus(snapshot, { simulateFailure: true, delayMs: 0 })).rejects.toThrow(
      'scénario de démonstration',
    )
    const result = await refreshNodeStatus(snapshot, { delayMs: 0, now })
    expect(result).toEqual({ status: nodeStatus(snapshot), checkedAt: now.toISOString() })
  })

  it('maps the demo scenario names', () => {
    expect(scenarioFromSearch('?demo=noeud-en-ligne')).toBe('node-online')
    expect(scenarioFromSearch('?demo=noeud-degrade')).toBe('node-degraded')
    expect(scenarioFromSearch('?demo=noeud-hors-ligne')).toBe('node-offline')
  })
})
