import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  applyChecklist,
  INSTALLATION_STEP_COUNT,
  installationGuide,
  registrationRequest,
} from '../src/services/installationService'
import { configFileJson, nodeConfiguration } from '../src/services/nodeConfigService'
import { applyDownload, preparePackage } from '../src/services/nodePackageService'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  loadOnboardingSnapshot,
  type DemoScenario,
} from '../src/services/onboardingService'

const now = new Date('2026-10-10T18:00:00+01:00')
const load = (scenario: DemoScenario = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })
const repo = (path: string) => fileURLToPath(new URL(`../../../../${path}`, import.meta.url))
const step = (guide: NonNullable<ReturnType<typeof installationGuide>>, id: string) => guide.find((s) => s.id === id)!

function hasPython(): boolean {
  try {
    execFileSync('python3', ['--version'])
    return true
  } catch {
    return false
  }
}

describe('Hospital Node installation guide', () => {
  it('is available only after an approval', async () => {
    expect(installationGuide(await load())).toBeNull()
    expect(installationGuide(await load('decision-rejected'))).toBeNull()
    expect(installationGuide(await load('decision-approved'))).toHaveLength(INSTALLATION_STEP_COUNT)
  })

  it('follows the vision flow and labels what is not built or not decided', async () => {
    const guide = installationGuide(await load('decision-approved'))!
    expect(guide.map((s) => [s.id, s.status])).toEqual([
      ['admin-approval', 'requirement'],
      ['environment', 'demo'],
      ['verify-package', 'demo'],
      ['container-runtime', 'open'],
      ['configuration', 'demo'],
      ['local-secrets', 'planned'],
      ['launch', 'demo'],
      ['health-check', 'demo'],
      ['registration', 'demo'],
    ])
    expect(step(guide, 'local-secrets').commands).toBeUndefined()
    expect(step(guide, 'container-runtime').commands).toBeUndefined()
    expect(step(guide, 'launch').warning).toContain('refuserait de démarrer')
  })

  it('uses the real Node port, config file, health endpoint, and the recorded checksum', async () => {
    const approved = await load('decision-approved')
    const prepared = await preparePackage(approved, { stepMs: 0, now })
    const guide = installationGuide(applyDownload(approved, prepared, now.toISOString()))!
    expect(step(guide, 'verify-package').commands).toBe('sha256sum node-hospital-c-package-demo.json')
    expect(step(guide, 'verify-package').body).toContain(prepared.sha256)
    expect(step(guide, 'launch').commands).toContain('HOSPITAL_NODE_CONFIG=config/hospital-c.json python main.py')
    expect(step(guide, 'health-check').commands).toBe('curl http://127.0.0.1:8103/health')
    expect(readFileSync(repo('instances/hospital-node/requirements.txt'), 'utf-8').length).toBeGreaterThan(0)
  })

  it('sends a registration body with exactly the Federation contract required fields', async () => {
    const snapshot = await load('decision-approved')
    const body = registrationRequest(snapshot)!
    const contract = readFileSync(repo('contracts/federation/node-registry.v1.yaml'), 'utf-8')
    const section = contract.slice(contract.indexOf('    RegistrationRequest:'))
    const required = section.match(/required: \[([^\]]+)\]/)![1].split(',').map((f) => f.trim())
    expect(Object.keys(body).sort()).toEqual([...required].sort())
    expect(body).toEqual({
      organization_ref: 'org-hospital-c',
      base_url: 'http://localhost:8103',
      contract_versions: ['1.0'],
      approval_decision_ref: snapshot.decision!.id,
    })
    expect(step(installationGuide(snapshot)!, 'registration').commands).toContain(
      'curl -X PUT http://localhost:8300/v1/registry/nodes/node-hospital-c',
    )
  })

  it.skipIf(!hasPython())('extracts the exact Node configuration with the shown command', async () => {
    const approved = await load('decision-approved')
    const prepared = await preparePackage(approved, { stepMs: 0, now })
    const dir = mkdtempSync(join(tmpdir(), 'hc062-'))
    writeFileSync(join(dir, prepared.fileName), prepared.json)
    const command = step(installationGuide(approved)!, 'configuration').commands!
    // Run the documented one-liner, minus the redirection, from the package's folder.
    const pythonCode = command.match(/python3 -c "([^"]+)"/)![1]
    const output = execFileSync('python3', ['-c', pythonCode, prepared.fileName], { cwd: dir, encoding: 'utf-8' })
    const config = nodeConfiguration(approved)
    if (config.kind !== 'ready') throw new Error('expected a configuration')
    expect(JSON.parse(output)).toEqual(JSON.parse(configFileJson(config.summary.file)))
    expect(command).toContain('> instances/hospital-node/config/hospital-c.json')
  })

  it('tracks declared steps without verifying them', async () => {
    let snapshot = await load('decision-approved')
    const installation = () => snapshot.steps.find((s) => s.id === 'node-installation')!
    expect(installation()).toMatchObject({ status: 'pending', detail: 'Installation non commencée.' })

    snapshot = applyChecklist(snapshot, 'admin-approval', true)
    snapshot = applyChecklist(snapshot, 'environment', true)
    expect(installation()).toMatchObject({ status: 'in_progress', detail: `2 / ${INSTALLATION_STEP_COUNT} étapes déclarées effectuées.` })

    for (const s of installationGuide(snapshot)!) snapshot = applyChecklist(snapshot, s.id, true)
    expect(installation()).toMatchObject({ status: 'completed', detail: 'Installation déclarée terminée (non vérifiée).' })
    expect(snapshot.steps.find((s) => s.id === 'node-status')?.status).not.toBe('completed')

    snapshot = applyChecklist(snapshot, 'environment', false)
    expect(installation().status).toBe('in_progress')
    expect(() => applyChecklist(snapshot, 'unknown', true)).toThrow('inconnue')
    const pending = await load()
    expect(() => applyChecklist(pending, 'environment', true)).toThrow("qu'après l'approbation")
  })
})
