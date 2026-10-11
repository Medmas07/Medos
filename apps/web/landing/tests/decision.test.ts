import { describe, expect, it } from 'vitest'
import { applyUpload, canUpload, documentChecklist, uploadDocument } from '../src/services/documentService'
import { humanReviewState } from '../src/services/humanReviewService'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  loadOnboardingSnapshot,
  scenarioFromSearch,
  type DemoScenario,
} from '../src/services/onboardingService'
import type { OnboardingSnapshot } from '../src/types/onboarding'

const load = (scenario: DemoScenario = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })
const status = (snapshot: OnboardingSnapshot, id: string) => snapshot.steps.find((s) => s.id === id)!

describe('Hospital approval page: Governance decision', () => {
  it('keeps the canonical Cap Azur application without a decision', async () => {
    const snapshot = await load()
    expect(snapshot.decision).toBeNull()
    expect(snapshot.application!.status).toBe('human_review')
    expect(status(snapshot, 'decision').status).toBe('pending')
    expect(status(snapshot, 'node-configuration').status).toBe('locked')
  })

  it('maps the decision scenario parameters', () => {
    expect(scenarioFromSearch('?demo=decision-approuvee')).toBe('decision-approved')
    expect(scenarioFromSearch('?demo=decision-refusee')).toBe('decision-rejected')
  })

  it('shows a simulated approval as received from Governance, with a condition, unlocking the Node', async () => {
    const snapshot = await load('decision-approved')
    expect(snapshot.decision).toMatchObject({
      outcome: 'approved',
      subjectId: 'app-hospital-c',
      simulated: true,
      conditions: ["Fournir l'attestation d'assurance avant la mise en service du Hospital Node."],
    })
    expect(snapshot.application).toMatchObject({ status: 'approved', decisionId: snapshot.decision!.id })
    expect(snapshot.organization).toMatchObject({ governanceStatus: 'approved', approvalDecisionId: snapshot.decision!.id })
    expect(humanReviewState(snapshot.application)).toMatchObject({ kind: 'completed', decided: true })
    expect(status(snapshot, 'decision').status).toBe('completed')
    expect(status(snapshot, 'node-configuration')).toMatchObject({ status: 'completed', detail: 'Configuration prête : node-hospital-c.' })
    expect(status(snapshot, 'node-download').status).toBe('pending')
  })

  it('lets an approved application provide the document its decision conditions require', async () => {
    const snapshot = await load('decision-approved')
    const insurance = documentChecklist(snapshot.application!).find((d) => d.type === 'insurance_certificate')!
    expect(canUpload(snapshot.application!, insurance)).toBe(true)
    expect(status(snapshot, 'documents')).toMatchObject({ status: 'attention', detail: '1 document à fournir.' })

    const file = { name: 'assurance.pdf', size: 1000, type: 'application/pdf' }
    const next = applyUpload(snapshot, 'insurance_certificate', await uploadDocument(file, { stepMs: 0 }))
    expect(status(next, 'documents').status).toBe('completed')
    const statutes = documentChecklist(next.application!).find((d) => d.type === 'statutes')!
    expect(canUpload(next.application!, statutes)).toBe(false)
  })

  it('shows a simulated rejection that keeps the Node and the documents locked', async () => {
    const snapshot = await load('decision-rejected')
    expect(snapshot.decision).toMatchObject({ outcome: 'rejected', conditions: [], simulated: true })
    expect(snapshot.organization.approvalDecisionId).toBeNull()
    expect(status(snapshot, 'decision').status).toBe('rejected')
    for (const id of ['documents', 'automated-review']) {
      expect(status(snapshot, id)).toEqual(expect.objectContaining({ status: 'locked', detail: 'Verrouillé : candidature rejetée.' }))
    }
    expect(snapshot.steps.filter((s) => s.status === 'attention')).toEqual([])
    expect(status(snapshot, 'node-download').status).toBe('locked')
    for (const document of documentChecklist(snapshot.application!)) {
      expect(canUpload(snapshot.application!, document)).toBe(false)
    }
  })

  it('never exposes a decision without a submitted application', async () => {
    const empty = await load('empty')
    expect(empty.application).toBeNull()
    expect(empty.decision).toBeNull()
  })
})
