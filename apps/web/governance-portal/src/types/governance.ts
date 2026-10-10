/**
 * Types for the Governance / Ethics Authority domain.
 * Aligned with contracts and canonical demo fixtures (demo-data/).
 */

export type SubjectType =
  | 'hospital_application'
  | 'synchronization_request'
  | 'research_access_request'
  | 'decision'

export type DecisionOutcome = 'approved' | 'rejected' | 'under_review' | 'pending'

export interface HospitalDocument {
  id: string
  title: string
  status: 'received' | 'missing' | 'rejected'
}

export interface HospitalAgreement {
  code: string
  title: string
  accepted: boolean
}

export interface TechnicalQuestionnaire {
  operatingSystem: string
  dmiSystem: string
  database: string
  network: string
  technicalContactId: string
}

export interface ReviewStep {
  step: 'completeness_check' | 'assisted_review' | 'human_review'
  status: 'pending' | 'completed' | 'completed_with_findings'
  completedAt: string | null
  reviewerId?: string
  mocked?: boolean
  advisory?: boolean
  findings: string[]
}

export interface HospitalApplication {
  id: string
  organizationId: string
  submittedById: string | null
  submittedAt: string
  status: 'human_review' | 'approved' | 'rejected' | 'pending'
  documents: HospitalDocument[]
  agreements: HospitalAgreement[]
  technicalQuestionnaire: TechnicalQuestionnaire | null
  reviewSteps: ReviewStep[]
  decisionId: string | null
}

export interface ConsentInfo {
  basis: 'patient_grant' | 'signed_consent_form' | 'emergency_override' | 'none'
  accessGrantId: string | null
}

export interface SynchronizationRequest {
  id: string
  requesterOrganizationId: string
  targetOrganizationId: string
  patientId: string
  purpose: string
  scope: string[]
  durationDays: number
  consent: ConsentInfo
  status: 'pending' | 'approved' | 'rejected'
  submittedAt: string
  decisionId: string | null
}

export interface ResearchAccessRequest {
  id: string
  projectId: string
  submittedById: string
  submittedAt: string
  status: 'approved' | 'under_review' | 'rejected'
  decisionId: string | null
}

export interface ResearchProjectInfo {
  id: string
  title: string
  principalInvestigatorId: string
  organizationId: string
  status: 'approved' | 'under_review' | 'rejected'
  createdAt: string
  summary: string
  population: string
  variables: string[]
  participatingOrganizationIds: string[]
  protocolDocument?: { id: string; title: string }
  researchAccessRequestId?: string
}

export interface GovernanceDecision {
  id: string
  subjectType: SubjectType
  subjectId: string
  outcome: 'approved' | 'rejected'
  decidedById: string
  decidedAt: string
  rationale: string
  conditions: string[]
  validUntil: string | null
  /** True for a decision recorded only in local portal state (HC-073), never persisted. */
  simulated?: boolean
  /**
   * What an approved research access request authorizes (HC-078). Mirrors the
   * Authorization and output policy of contracts/api/research/research-node-execution.v1.yaml.
   */
  researchAuthorization?: ResearchAuthorization
}

export interface ResearchAuthorization {
  approvedOrganizationIds: string[]
  approvedVariables: string[]
  minimumCellSize: number
}

export interface GovernanceAuditEvent {
  id: string
  at: string
  actorId: string | null
  action: 'decision_recorded' | 'application_submitted' | 'request_received' | 'proof_verified'
  subjectType: SubjectType
  subjectId: string
  organizationIds: string[]
  /** True for an event recorded only in local portal state (HC-073), never persisted. */
  simulated?: boolean
}

export interface AnchoredPayload {
  eventId: string
  decisionId: string
  outcome: string
  decidedAt: string
  organizationIds: string[]
  version: number
}

export interface LedgerProof {
  id: string
  auditEventId: string
  simulated: boolean
  ledger: string
  anchoredPayload: AnchoredPayload
  hashAlgorithm: string
  hash: string
  anchoredAt: string
  verificationStatus: 'verified' | 'tampered' | 'unverified'
}

export interface OrganizationInfo {
  id: string
  type: string
  name: string
  shortName: string
  city: string
  governanceStatus: string | null
  node?: {
    id: string
    status: string
    version: string
    lastSyncAt: string
    dmiState: string
  } | null
}

/** A patient's access grant (demo-data/access.json), referenced by a synchronization's consent. */
export interface AccessGrant {
  id: string
  patientId: string
  granteeId: string
  scope: string[]
  purpose: string
  status: 'active' | 'expired' | 'revoked'
  grantedAt: string
  expiresAt: string
  revokedAt: string | null
}

export interface PersonInfo {
  id: string
  title?: string | null
  firstName: string
  lastName: string
  role?: string
  organizationId?: string
}

export interface PatientInfo {
  id: string
  federatedId: string
  firstName: string
  lastName: string
  city: string
}

export interface GovernanceNotification {
  id: string
  recipientId: string
  type: string
  title: string
  body: string
  createdAt: string
  read: boolean
  relatedId?: string | null
}

