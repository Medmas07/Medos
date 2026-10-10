import accessFixtures from '../../../../../demo-data/access.json'
import governanceFixtures from '../../../../../demo-data/governance.json'
import notificationsFixtures from '../../../../../demo-data/notifications.json'
import organizationsFixtures from '../../../../../demo-data/organizations.json'
import peopleFixtures from '../../../../../demo-data/people.json'
import researchFixtures from '../../../../../demo-data/research.json'
import type {
  AccessGrant,
  GovernanceAuditEvent,
  GovernanceDecision,
  GovernanceNotification,
  HospitalApplication,
  LedgerProof,
  OrganizationInfo,
  PatientInfo,
  PersonInfo,
  ResearchAccessRequest,
  ResearchProject,
  SynchronizationRequest,
} from '../types/governance'
import { reviewStore } from './reviewStore'

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

const typedAccessGrants = (accessFixtures.accessGrants ?? []) as unknown as AccessGrant[]

const typedProjects = (researchFixtures.projects ?? []) as unknown as ResearchProject[]

const typedOrganizations = (organizationsFixtures.organizations ?? []) as unknown as OrganizationInfo[]

const typedPatients = (peopleFixtures.patients ?? []) as unknown as PatientInfo[]

const typedNotifications = (notificationsFixtures.notifications ?? []) as unknown as GovernanceNotification[]

const allStaffAndClinicians = [
  ...((peopleFixtures.staff ?? []) as unknown as PersonInfo[]),
  ...((peopleFixtures.clinicians ?? []) as unknown as PersonInfo[]),
]

export const governanceService = {
  // Fixtures merged with the SIMULATED decisions recorded in this session (HC-073).
  getHospitalApplications(): HospitalApplication[] {
    const simulated = reviewStore.getSnapshot().applications
    return typedGovernance.hospitalApplications.map((app) => simulated[app.id] ?? app)
  },

  // Read through getHospitalApplications so simulated decisions (HC-073) leave the queue.
  getPendingHospitalApplications(): HospitalApplication[] {
    return this.getHospitalApplications().filter(
      (app) => app.status === 'human_review' || app.status === 'pending'
    )
  },

  getHospitalApplication(id: string): HospitalApplication | undefined {
    return this.getHospitalApplications().find((app) => app.id === id)
  },

  // Fixtures merged with the SIMULATED decisions recorded in this session (HC-076).
  getSynchronizationRequests(): SynchronizationRequest[] {
    const simulated = reviewStore.getSnapshot().synchronizationRequests
    return typedGovernance.synchronizationRequests.map((req) => simulated[req.id] ?? req)
  },

  getAccessGrant(id: string | null): AccessGrant | undefined {
    if (!id) return undefined
    return typedAccessGrants.find((g) => g.id === id)
  },

  // Fixtures merged with the SIMULATED decisions recorded in this session (HC-078).
  getResearchAccessRequests(): ResearchAccessRequest[] {
    const simulated = reviewStore.getSnapshot().researchAccessRequests
    return typedGovernance.researchAccessRequests.map((req) => simulated[req.id] ?? req)
  },

  getResearchProject(id: string): ResearchProject | undefined {
    return typedProjects.find((p) => p.id === id)
  },

  getDecisions(): GovernanceDecision[] {
    return [...typedGovernance.decisions, ...reviewStore.getSnapshot().decisions]
  },

  getAuditEvents(): GovernanceAuditEvent[] {
    return [...typedGovernance.auditEvents, ...reviewStore.getSnapshot().auditEvents]
  },

  getLedgerProofs(): LedgerProof[] {
    return typedGovernance.ledgerProofs
  },

  getOrganizations(): OrganizationInfo[] {
    return typedOrganizations
  },

  getFederatedHospitalNodes(): OrganizationInfo[] {
    return typedOrganizations.filter(
      (org) => org.type === 'hospital' || org.type === 'private_practice'
    )
  },

  getReviewerNotifications(recipientId: string = 'usr-olfa'): GovernanceNotification[] {
    return typedNotifications.filter((n) => n.recipientId === recipientId)
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
    return this.getDecisions().find((d) => d.id === id)
  },

  getProofForEvent(eventId: string): LedgerProof | undefined {
    return typedGovernance.ledgerProofs.find((p) => p.auditEventId === eventId)
  },

  getDashboardMetrics() {
    const applications = this.getHospitalApplications()
    const syncs = this.getSynchronizationRequests()
    const research = this.getResearchAccessRequests()
    const proofs = this.getLedgerProofs()
    const notifications = this.getReviewerNotifications('usr-olfa')
    const nodes = this.getFederatedHospitalNodes()

    return {
      totalApplications: applications.length,
      pendingApplications: applications.filter(
        (a) => a.status === 'human_review' || a.status === 'pending'
      ).length,
      approvedHospitals: applications.filter((a) => a.status === 'approved').length,
      totalSyncs: syncs.length,
      pendingSyncs: syncs.filter((s) => s.status === 'pending').length,
      approvedSyncs: syncs.filter((s) => s.status === 'approved').length,
      rejectedSyncs: syncs.filter((s) => s.status === 'rejected').length,
      totalResearchRequests: research.length,
      underReviewResearch: research.filter((r) => r.status === 'under_review').length,
      approvedResearch: research.filter((r) => r.status === 'approved').length,
      anchoredProofsCount: proofs.length,
      unreadNotificationsCount: notifications.filter((n) => !n.read).length,
      onlineNodesCount: nodes.filter((n) => n.node?.status === 'online').length,
      degradedNodesCount: nodes.filter((n) => n.node?.status === 'degraded').length,
      pendingNodesCount: nodes.filter((n) => !n.node).length,
    }
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
