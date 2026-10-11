import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  configFileJson,
  NODE_CONFIG_KEYS,
  nodeConfiguration,
  nodeRefFor,
  OPAQUE_REF_PATTERN,
} from '../src/services/nodeConfigService'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  loadOnboardingSnapshot,
  type DemoScenario,
} from '../src/services/onboardingService'

const load = (scenario: DemoScenario = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })
const repo = (path: string) => fileURLToPath(new URL(`../../../../${path}`, import.meta.url))

describe('Hospital Node configuration summary', () => {
  it('stays in sync with the fields the Hospital Node configuration loader accepts', () => {
    const source = readFileSync(repo('instances/hospital-node/infrastructure/config.py'), 'utf-8')
    const model = source.slice(source.indexOf('class _ConfigFile'), source.indexOf('def config_path_from_env'))
    const fields = [...model.matchAll(/^ {4}([a-z_]+):/gm)].map((m) => m[1])
    expect([...fields].sort()).toEqual([...NODE_CONFIG_KEYS].sort())
    for (const name of ['hospital-a', 'hospital-b', 'private-practice']) {
      const demo = JSON.parse(readFileSync(repo(`instances/hospital-node/config/${name}.demo.json`), 'utf-8'))
      expect(Object.keys(demo).every((key) => (NODE_CONFIG_KEYS as readonly string[]).includes(key))).toBe(true)
    }
  })

  it('derives Federation-valid node references', () => {
    expect(nodeRefFor('org-hospital-c')).toBe('node-hospital-c')
    expect(OPAQUE_REF_PATTERN.test(nodeRefFor('org-hospital-a'))).toBe(true)
    expect(() => nodeRefFor('org-hôpital')).toThrow('invalide')
  })

  it('generates nothing before an approval', async () => {
    expect(nodeConfiguration(await load())).toEqual({ kind: 'awaiting_decision' })
    expect(nodeConfiguration(await load('empty'))).toEqual({ kind: 'no_application' })
    expect(nodeConfiguration(await load('decision-rejected'))).toMatchObject({ kind: 'rejected' })
  })

  it('builds the approved Cap Azur configuration from ADR-0003 and the approval reference', async () => {
    const snapshot = await load('decision-approved')
    const availability = nodeConfiguration(snapshot)
    if (availability.kind !== 'ready') throw new Error('expected a configuration')
    const { summary } = availability
    expect(summary.file).toMatchObject({
      node_ref: 'node-hospital-c',
      organization_ref: 'org-hospital-c',
      port: 8103,
      storage_dir: '../.storage/hospital-c',
      mock_access_grants: '../../../demo-data/access.json',
      mock_governance_decisions: '../../../demo-data/governance.json',
    })
    expect(summary.approvalDecisionRef).toBe(snapshot.decision!.id)
    expect(summary.federationBaseUrl).toBe('http://localhost:8103')
    expect(summary.environment?.hostingType).toBe('virtual_machine')
  })

  it('states that the current Node cannot start without a fictional records file for Hospital C', async () => {
    const availability = nodeConfiguration(await load('decision-approved'))
    if (availability.kind !== 'ready') throw new Error('expected a configuration')
    expect(availability.summary.blockers).toHaveLength(1)
    expect(availability.summary.blockers[0]).toContain('refuserait de démarrer')
  })

  it('writes the file with exactly the loader fields, in order, and no secret', async () => {
    const availability = nodeConfiguration(await load('decision-approved'))
    if (availability.kind !== 'ready') throw new Error('expected a configuration')
    const json = configFileJson(availability.summary.file)
    expect(Object.keys(JSON.parse(json))).toEqual([...NODE_CONFIG_KEYS])
    expect(json.toLowerCase()).not.toMatch(/password|secret|token|private_key|certificate/)
  })

  it('marks the configuration step ready once approved', async () => {
    const snapshot = await load('decision-approved')
    expect(snapshot.steps.find((s) => s.id === 'node-configuration')).toMatchObject({
      status: 'completed',
      detail: 'Configuration prête : node-hospital-c.',
    })
  })
})
