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

  it('computes accurate dashboard metrics across all governance domains', () => {
    const metrics = governanceService.getDashboardMetrics()
    expect(metrics.totalApplications).toBeGreaterThanOrEqual(4)
    expect(metrics.pendingApplications).toBe(1)
    expect(metrics.approvedHospitals).toBe(3)
    expect(metrics.totalSyncs).toBe(3)
    expect(metrics.pendingSyncs).toBe(1)
    expect(metrics.totalResearchRequests).toBe(2)
    expect(metrics.underReviewResearch).toBe(1)
    expect(metrics.anchoredProofsCount).toBe(2)
    expect(metrics.onlineNodesCount).toBeGreaterThanOrEqual(2)
    expect(metrics.degradedNodesCount).toBe(1)
  })

  it('retrieves reviewer alerts for Pr Olfa Hamdi', () => {
    const notifs = governanceService.getReviewerNotifications('usr-olfa')
    expect(notifs.length).toBeGreaterThanOrEqual(2)
    expect(notifs.some((n) => n.relatedId === 'sync-001')).toBe(true)
    expect(notifs.some((n) => n.relatedId === 'app-hospital-c')).toBe(true)
  })

  it('retrieves federated hospital nodes with node connectivity details', () => {
    const nodes = governanceService.getFederatedHospitalNodes()
    expect(nodes.length).toBe(4)

    const babEnnour = nodes.find((n) => n.id === 'org-hospital-a')
    expect(babEnnour?.node?.status).toBe('online')
    expect(babEnnour?.node?.dmiState).toBe('connected')

    const bouzid = nodes.find((n) => n.id === 'org-private-practice')
    expect(bouzid?.node?.status).toBe('degraded')
    expect(bouzid?.node?.dmiState).toBe('disconnected')
  })

  it('filters and accesses pending hospital applications for HC-072', () => {
    const pendingApps = governanceService.getPendingHospitalApplications()
    expect(pendingApps.length).toBe(1)

    const capAzur = pendingApps[0]
    expect(capAzur.id).toBe('app-hospital-c')
    expect(capAzur.status).toBe('human_review')
    expect(capAzur.organizationId).toBe('org-hospital-c')

    // Document checklist verification
    const missingDocs = capAzur.documents.filter((d) => d.status === 'missing')
    expect(missingDocs.length).toBe(1)
    expect(missingDocs[0].id).toBe('doc-c-assurance')

    // Technical questionnaire
    expect(capAzur.technicalQuestionnaire).toBeDefined()
    expect(capAzur.technicalQuestionnaire?.operatingSystem).toBe('Ubuntu Server 22.04')
    expect(capAzur.technicalQuestionnaire?.dmiSystem).toContain('MediDossier')

    // AI advisory observations
    const aiReview = capAzur.reviewSteps.find((s) => s.step === 'assisted_review')
    expect(aiReview?.advisory).toBe(true)
    expect(aiReview?.mocked).toBe(true)
    expect(aiReview?.findings.length).toBe(2)

    // Lookup by id
    const found = governanceService.getHospitalApplication('app-hospital-c')
    expect(found).toEqual(capAzur)
    const notFound = governanceService.getHospitalApplication('app-unknown')
    expect(notFound).toBeUndefined()
  })
})
