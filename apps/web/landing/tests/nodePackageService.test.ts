import { createHash } from 'node:crypto'
import { describe, expect, it } from 'vitest'
import { configFileJson, NODE_CONFIG_KEYS, nodeConfiguration } from '../src/services/nodeConfigService'
import {
  applyDownload,
  buildManifest,
  NOT_INCLUDED,
  PREPARATION_STEPS,
  preparePackage,
  sha256Hex,
} from '../src/services/nodePackageService'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  loadOnboardingSnapshot,
  scenarioFromSearch,
  type DemoScenario,
} from '../src/services/onboardingService'

const now = new Date('2026-10-10T17:00:00+01:00')
const load = (scenario: DemoScenario = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })
const prepare = async (scenario: DemoScenario = 'decision-approved', simulateFailure = false) =>
  preparePackage(await load(scenario), { stepMs: 0, now, simulateFailure })

describe('Hospital Node download page: demo package', () => {
  it('offers no package before approval or after a rejection', async () => {
    expect(buildManifest(await load(), now.toISOString())).toBeNull()
    expect(buildManifest(await load('decision-rejected'), now.toISOString())).toBeNull()
    await expect(prepare('nominal')).rejects.toThrow("qu'après l'approbation")
  })

  it('embeds exactly the HC-060 Node configuration and the approval reference', async () => {
    const snapshot = await load('decision-approved')
    const manifest = buildManifest(snapshot, now.toISOString())!
    const config = nodeConfiguration(snapshot)
    if (config.kind !== 'ready') throw new Error('expected a configuration')
    expect(Object.keys(manifest.hospitalNodeConfig)).toEqual([...NODE_CONFIG_KEYS])
    expect(JSON.stringify(manifest.hospitalNodeConfig, null, 2)).toBe(configFileJson(config.summary.file))
    expect(manifest.node).toEqual({
      nodeRef: 'node-hospital-c',
      organizationRef: 'org-hospital-c',
      approvalDecisionRef: snapshot.decision!.id,
    })
    expect(manifest.knownLimitations).toEqual(config.summary.blockers)
  })

  it('states what is not included and why, and holds no secret or executable', async () => {
    const manifest = buildManifest(await load('decision-approved'), now.toISOString())!
    expect(manifest.fictional).toBe(true)
    expect(manifest.notIncluded.map((i) => [i.item, i.status])).toEqual([
      ['containerImages', 'installation_package'],
      ['nodeIdentity', 'planned'],
      ['installationHelper', 'installation_package'],
    ])
    expect(manifest.notIncluded).toBe(NOT_INCLUDED)
    const text = JSON.stringify(manifest).toLowerCase()
    expect(text).not.toMatch(/"(password|secret|token|private_?key|certificate)"\s*:/)
    expect(text).not.toMatch(/\.(sh|exe|bat|ps1|msi)\b/)
    expect(manifest.dmiAdapter).toMatchObject({ status: 'planned', dmiSystem: 'MediDossier v7 (logiciel fictif)' })
  })

  it('computes a SHA-256 checksum that matches an independent computation', async () => {
    const prepared = await prepare()
    expect(prepared.fileName).toBe('node-hospital-c-package-demo.json')
    expect(prepared.sha256).toBe(createHash('sha256').update(prepared.json, 'utf8').digest('hex'))
    expect(prepared.sizeBytes).toBe(Buffer.byteLength(prepared.json, 'utf8'))
    expect(JSON.parse(prepared.json).generatedAt).toBe(now.toISOString())
    expect(await sha256Hex('')).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
  })

  it('reports each preparation step, and fails explicitly in the failure scenario', async () => {
    const steps: number[] = []
    await preparePackage(await load('decision-approved'), { stepMs: 0, now, onStep: (i) => steps.push(i) })
    expect(steps).toEqual(PREPARATION_STEPS.map((_, i) => i))
    await expect(prepare('decision-approved', true)).rejects.toThrow('a échoué')
    expect(scenarioFromSearch('?demo=echec-telechargement')).toBe('download-failure')
    expect((await load('download-failure')).decision?.outcome).toBe('approved')
  })

  it('records the download and completes the download step only', async () => {
    const snapshot = await load('decision-approved')
    const prepared = await prepare()
    const next = applyDownload(snapshot, prepared, now.toISOString())
    expect(next.application!.nodePackage).toEqual({
      fileName: prepared.fileName,
      sha256: prepared.sha256,
      sizeBytes: prepared.sizeBytes,
      generatedAt: prepared.generatedAt,
      downloadedAt: now.toISOString(),
    })
    const step = (id: string) => next.steps.find((s) => s.id === id)!
    expect(step('node-download')).toMatchObject({ status: 'completed', detail: 'Package téléchargé : node-hospital-c-package-demo.json.' })
    expect(step('node-installation').status).toBe('pending')
    expect(() => applyDownload(snapshot, prepared, now.toISOString())).not.toThrow()
    const pending = await load()
    expect(() => applyDownload(pending, prepared, now.toISOString())).toThrow("qu'après l'approbation")
  })
})
