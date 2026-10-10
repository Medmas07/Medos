import governanceFixtures from '../../../../../demo-data/governance.json'
import organizationsFixtures from '../../../../../demo-data/organizations.json'
import peopleFixtures from '../../../../../demo-data/people.json'
import type {
  GovernanceAuditEvent,
  GovernanceDecision,
  HospitalApplication,
  LedgerProof,
  OrganizationInfo,
  PatientInfo,
  PersonInfo,
  ResearchAccessRequest,
  SynchronizationRequest,
} from '../types/governance'

const typedGovernance = governanceFixtures as unknown as {
  fictional: boolean
  notice: string
  hospitalApplications: HospitalApplication[]
  synchronizationRequests: SynchronizationRequest[]
  researchAccessRequests: ResearchAccessRequest[]
  decisions: GovernanceDecision[]
  auditEvents: GovernanceAuditEvent[]
  ledgerProofs: LedgerProof[]
}

const typedOrganizations = (organizationsFixtures.organizations ?? []) as unknown as OrganizationInfo[]

const typedPatients = (peopleFixtures.patients ?? []) as unknown as PatientInfo[]

const allStaffAndClinicians = [
  ...((peopleFixtures.staff ?? []) as unknown as PersonInfo[]),
  ...((peopleFixtures.clinicians ?? []) as unknown as PersonInfo[]),
]

export const governanceService = {
  getHospitalApplications(): HospitalApplication[] {
    return typedGovernance.hospitalApplications
  },

  getSynchronizationRequests(): SynchronizationRequest[] {
    return typedGovernance.synchronizationRequests
  },

  getResearchAccessRequests(): ResearchAccessRequest[] {
    return typedGovernance.researchAccessRequests
  },

  getDecisions(): GovernanceDecision[] {
    return typedGovernance.decisions
  },

  getAuditEvents(): GovernanceAuditEvent[] {
    return typedGovernance.auditEvents
  },

  getLedgerProofs(): LedgerProof[] {
    return typedGovernance.ledgerProofs
  },

  getOrganization(id: string): OrganizationInfo | undefined {
    return typedOrganizations.find((org) => org.id === id)
  },

  getOrganizationName(id: string): string {
    const org = this.getOrganization(id)
    return org ? org.name : id
  },

  getPerson(id: string): PersonInfo | undefined {
    return allStaffAndClinicians.find((p) => p.id === id)
  },

  getPersonName(id: string | null): string {
    if (!id) return 'Système automatisé'
    const person = this.getPerson(id)
    if (!person) return id
    const prefix = person.title ? `${person.title} ` : ''
    return `${prefix}${person.firstName} ${person.lastName}`
  },

  getPatient(id: string): PatientInfo | undefined {
    return typedPatients.find((p) => p.id === id)
  },

  getDecision(id: string | null): GovernanceDecision | undefined {
    if (!id) return undefined
    return typedGovernance.decisions.find((d) => d.id === id)
  },

  getProofForEvent(eventId: string): LedgerProof | undefined {
    return typedGovernance.ledgerProofs.find((p) => p.auditEventId === eventId)
  },

  /**
   * Deterministic client-side SHA-256 hash calculation using Web Crypto API.
   * Produces the exact hexadecimal representation.
   */
  async computeSha256(data: string): Promise<string> {
    const encoder = new TextEncoder()
    const buffer = encoder.encode(data)
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
  },

  /**
   * Canonical JSON stringifier matching Python check_fixtures.py format:
   * json.dumps(payload, sort_keys=True, separators=(',', ':'))
   */
  canonicalJson(obj: unknown): string {
    return JSON.stringify(obj, Object.keys(obj as object).sort())
  },
}
