import { describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'

describe('Governance Service & Canonical Fixtures', () => {
  it('loads canonical hospital applications with expected review steps', () => {
    const apps = governanceService.getHospitalApplications()
    expect(apps.length).toBeGreaterThanOrEqual(4)

    const capAzur = apps.find((a) => a.id === 'app-hospital-c')
    expect(capAzur).toBeDefined()
    expect(capAzur?.status).toBe('human_review')
    expect(capAzur?.documents.length).toBe(3)
    expect(capAzur?.agreements.length).toBe(2)

    // Check completeness check findings
    const completeness = capAzur?.reviewSteps.find((s) => s.step === 'completeness_check')
    expect(completeness?.findings).toContain("Attestation d'assurance manquante.")

    // Check AI assisted review is advisory and mocked
    const aiStep = capAzur?.reviewSteps.find((s) => s.step === 'assisted_review')
    expect(aiStep?.advisory).toBe(true)
    expect(aiStep?.mocked).toBe(true)
    expect(aiStep?.findings.length).toBeGreaterThan(0)
  })

  it('loads inter-hospital synchronization requests with explicit consent and purpose', () => {
    const syncs = governanceService.getSynchronizationRequests()
    expect(syncs.length).toBe(3)

    const sync1 = syncs.find((s) => s.id === 'sync-001')
    expect(sync1?.patientId).toBe('pat-a')
    expect(sync1?.consent.basis).toBe('patient_grant')
    expect(sync1?.status).toBe('pending')

    const sync2 = syncs.find((s) => s.id === 'sync-002')
    expect(sync2?.status).toBe('approved')
    expect(sync2?.decisionId).toBe('dec-sync-002')

    const sync3 = syncs.find((s) => s.id === 'sync-003')
    expect(sync3?.status).toBe('rejected')
    expect(sync3?.consent.basis).toBe('none')
  })

  it('loads research requests with Compute-to-Data constraint', () => {
    const research = governanceService.getResearchAccessRequests()
    expect(research.length).toBe(2)

    const rar1 = research.find((r) => r.id === 'rar-001')
    expect(rar1?.status).toBe('approved')
    const decision = governanceService.getDecision(rar1?.decisionId ?? null)
    expect(decision?.rationale).toContain('compute-to-data')
    expect(decision?.conditions).toContain('Aucune donnée individuelle en sortie.')
  })

  it('resolves organization and people metadata correctly', () => {
    const org = governanceService.getOrganization('org-governance')
    expect(org?.name).toContain('Gouvernance')

    const reviewer = governanceService.getPerson('usr-olfa')
    expect(reviewer?.firstName).toBe('Olfa')
    expect(reviewer?.lastName).toBe('Hamdi')
    expect(reviewer?.role).toBe('governance_reviewer')

    const pat = governanceService.getPatient('pat-a')
    expect(pat?.firstName).toBe('Leïla')
    expect(pat?.federatedId).toBe('FED-PAT-0001')
  })

  it('validates cryptographic SHA-256 hash matching on simulated ledger proofs', async () => {
    const proofs = governanceService.getLedgerProofs()
    expect(proofs.length).toBe(2)

    for (const proof of proofs) {
      expect(proof.simulated).toBe(true)
      expect(proof.hashAlgorithm).toBe('SHA-256')

      // Ensure no raw clinical data in proof payload
      const payloadKeys = Object.keys(proof.anchoredPayload)
      expect(payloadKeys).not.toContain('patient')
      expect(payloadKeys).not.toContain('diagnosis')
      expect(payloadKeys).not.toContain('medication')
      expect(payloadKeys).not.toContain('labReport')

      // Recompute SHA-256 hash
      const canonical = governanceService.canonicalJson(proof.anchoredPayload)
      const computed = await governanceService.computeSha256(canonical)
      expect(computed).toBe(proof.hash)
    }
  })
})
