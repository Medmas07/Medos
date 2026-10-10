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
}

export interface GovernanceAuditEvent {
  id: string
  at: string
  actorId: string | null
  action: 'decision_recorded' | 'application_submitted' | 'request_received' | 'proof_verified'
  subjectType: SubjectType
  subjectId: string
  organizationIds: string[]
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

export interface PersonInfo {
  id: string
  title?: string | null
  firstName: string
  lastName: string
  role?: string
}

export interface PatientInfo {
  id: string
  federatedId: string
  firstName: string
  lastName: string
  city: string
}
