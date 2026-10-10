import { describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'

describe('HC-075 — Synchronization Request Detail & Verification', () => {
  it('retrieves synchronization requests with distinct clinical contexts', () => {
    const syncs = governanceService.getSynchronizationRequests()
    expect(syncs.length).toBeGreaterThanOrEqual(3)

    const sync1 = governanceService.getSynchronizationRequest('sync-001')
    expect(sync1).toBeDefined()
    expect(sync1?.purpose).toContain('Continuité des soins')
    expect(sync1?.durationDays).toBe(30)
    expect(sync1?.status).toBe('pending')

    const sync2 = governanceService.getSynchronizationRequest('sync-002')
    expect(sync2).toBeDefined()
    expect(sync2?.status).toBe('approved')
    expect(sync2?.decisionId).toBe('dec-sync-002')

    const sync3 = governanceService.getSynchronizationRequest('sync-003')
    expect(sync3).toBeDefined()
    expect(sync3?.status).toBe('rejected')
    expect(sync3?.consent.basis).toBe('none')
  })

  it('resolves source and target hospital organizations with node and DMI status', () => {
    const sync1 = governanceService.getSynchronizationRequest('sync-001')!
    const reqOrg = governanceService.getOrganization(sync1.requesterOrganizationId)
    const tgtOrg = governanceService.getOrganization(sync1.targetOrganizationId)

    expect(reqOrg).toBeDefined()
    expect(reqOrg?.name).toBe('Hôpital Universitaire Bab Ennour')
    expect(reqOrg?.city).toBe('Tunis')
    expect(reqOrg?.node?.status).toBe('online')
    expect(reqOrg?.node?.dmiState).toBe('connected')

    expect(tgtOrg).toBeDefined()
    expect(tgtOrg?.name).toBe('Hôpital Régional Oued Zitoun')
    expect(tgtOrg?.city).toBe('Sfax')
    expect(tgtOrg?.node?.status).toBe('online')
    expect(tgtOrg?.node?.dmiState).toBe('connected')
  })

  it('resolves patient identity and local cross-establishment identifiers', () => {
    const sync1 = governanceService.getSynchronizationRequest('sync-001')!
    const patient = governanceService.getPatient(sync1.patientId)

    expect(patient).toBeDefined()
    expect(patient?.federatedId).toBe('FED-PAT-0001')
    expect(patient?.firstName).toBe('Leïla')
    expect(patient?.lastName).toBe('Mansouri')
    expect(patient?.birthDate).toBe('1968-04-17')
    expect(patient?.sex).toBe('female')

    // Local identifiers per hospital
    const babEnnourId = patient?.localIdentifiers?.find(
      (li) => li.organizationId === 'org-hospital-a'
    )
    const ouedZitounId = patient?.localIdentifiers?.find(
      (li) => li.organizationId === 'org-hospital-b'
    )

    expect(babEnnourId?.value).toBe('BEN-2024-08812')
    expect(ouedZitounId?.value).toBe('OZ-55031')
  })

  it('resolves clinical data scope and verifies categories', () => {
    const sync1 = governanceService.getSynchronizationRequest('sync-001')!
    expect(sync1.scope).toEqual(['medications', 'labReports'])

    const sync2 = governanceService.getSynchronizationRequest('sync-002')!
    expect(sync2.scope).toEqual(['encounters'])

    const sync3 = governanceService.getSynchronizationRequest('sync-003')!
    expect(sync3.scope).toEqual(['labReports'])
  })

  it('resolves active patient access grant and links to attending clinician', () => {
    const sync1 = governanceService.getSynchronizationRequest('sync-001')!
    expect(sync1.consent.basis).toBe('patient_grant')
    expect(sync1.consent.accessGrantId).toBe('grant-a-drx')

    const grant = governanceService.getAccessGrant(sync1.consent.accessGrantId)
    expect(grant).toBeDefined()
    expect(grant?.status).toBe('active')
    expect(grant?.patientId).toBe('pat-a')
    expect(grant?.granteeId).toBe('clin-x')
    expect(grant?.scope).toContain('medications')
    expect(grant?.scope).toContain('labReports')

    // Attending clinician
    const clinician = governanceService.getPerson(grant!.granteeId)
    expect(clinician).toBeDefined()
    expect(clinician?.firstName).toBe('Youssef')
    expect(clinician?.lastName).toBe('Gharbi')
    expect(clinician?.specialty).toBe('Cardiologie')
  })

  it('handles signed consent form basis appropriately', () => {
    const sync2 = governanceService.getSynchronizationRequest('sync-002')!
    expect(sync2.consent.basis).toBe('signed_consent_form')
    expect(sync2.consent.accessGrantId).toBeNull()
  })

  it('identifies missing consent and validates rejection decision rationale', () => {
    const sync3 = governanceService.getSynchronizationRequest('sync-003')!
    expect(sync3.consent.basis).toBe('none')

    const decision = governanceService.getDecision(sync3.decisionId)
    expect(decision).toBeDefined()
    expect(decision?.outcome).toBe('rejected')
    expect(decision?.rationale).toContain("absence d'autorisation du patient")
  })

  it('validates cryptographic audit proof for approved synchronization decision', async () => {
    const sync2 = governanceService.getSynchronizationRequest('sync-002')!
    const decision = governanceService.getDecision(sync2.decisionId)
    expect(decision).toBeDefined()
    expect(decision?.outcome).toBe('approved')

    const event = governanceService
      .getAuditEvents()
      .find((e) => e.subjectId === decision?.id)
    expect(event).toBeDefined()

    const proof = governanceService.getProofForEvent(event!.id)
    expect(proof).toBeDefined()
    expect(proof?.verificationStatus).toBe('verified')

    // Proof payload must only contain audit metadata, never clinical records
    const keys = Object.keys(proof!.anchoredPayload)
    expect(keys).not.toContain('patient')
    expect(keys).not.toContain('diagnosis')
    expect(keys).not.toContain('medication')
  })
})
