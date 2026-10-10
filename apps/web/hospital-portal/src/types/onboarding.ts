/**
 * Types for the hospital onboarding view of the Hospital Portal.
 * They mirror the canonical fictional fixtures in demo-data/ (HC-005); they are
 * not API contracts. Onboarding contracts are PLANNED.
 */

export interface NodeSummary {
  id: string
  status: 'online' | 'degraded' | 'offline'
  version: string
  lastSyncAt: string
  dmiState: 'connected' | 'disconnected'
}

export interface Organization {
  id: string
  type: string
  name: string
  shortName: string
  city: string
  governanceStatus: 'approved' | 'under_review' | 'rejected' | null
  approvalDecisionId: string | null
  node: NodeSummary | null
}

export interface StaffMember {
  id: string
  title?: string
  firstName: string
  lastName: string
  role: string
  organizationId: string
  /** Only set for a manager registered in this portal (local state). */
  email?: string
  phone?: string
}

export type DocumentType = 'statutes' | 'operating_license' | 'insurance_certificate'

/** Metadata of a file deposited in this portal (HC-053). The file content is never read or sent. */
export interface DocumentUpload {
  fileName: string
  sizeBytes: number
  mediaType: string
  uploadedAt: string
}

export interface ApplicationDocument {
  id: string
  type: DocumentType
  title: string
  status: 'received' | 'missing' | 'rejected'
  /** Only set for a document deposited in this portal (local state). */
  upload?: DocumentUpload
}

export type AgreementCode = 'data_processing_agreement' | 'governance_charter'

export interface ApplicationAgreement {
  code: AgreementCode
  title: string
  accepted: boolean
  /** Version of the agreement text that was accepted. */
  version?: string
  acceptedAt?: string
  acceptedById?: string
}

export type HostingType = 'on_premise' | 'virtual_machine' | 'private_cloud'

export type DmiHosting = 'on_premise' | 'vendor_hosted'
export type IntegrationMethod = 'hl7v2' | 'fhir_api' | 'file_export' | 'database_replica' | 'none'

/**
 * Technical questionnaire. The deployment environment of the future Hospital
 * Node is collected by HC-055; the DMI / HIS fields belong to HC-056.
 */
export interface TechnicalQuestionnaire {
  hostingType: HostingType
  operatingSystem: string
  cpuCores: number
  memoryGb: number
  storageGb: number
  bandwidthMbps: number
  /** Free-text description of the network. */
  network: string
  dmzAvailable: boolean
  outboundHttpsAllowed: boolean
  containerRuntimeAvailable: boolean
  backupsInPlace: boolean
  technicalContactId: string
  // DMI / HIS information (HC-056); absent until that page is completed.
  dmiSystem?: string
  database?: string
  dmiHosting?: DmiHosting
  integrationMethods?: IntegrationMethod[]
  testEnvironmentAvailable?: boolean
  dmiNotes?: string
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

export interface ProfileContact {
  fullName: string
  email: string
}

/** Administrative information of the establishment (HC-052). */
export interface AdministrativeProfile {
  legalName: string
  legalStatus: 'public' | 'private'
  registrationNumber: string
  bedCapacity: number
  address: { street: string; postalCode: string; city: string; governorate: string }
  phone: string
  email: string
  legalRepresentative: { fullName: string; role: string }
  dataProtectionOfficer: ProfileContact
  /** Recommended, not required: the assisted review flags its absence. */
  securityContact: ProfileContact | null
  updatedAt: string
}

export interface HospitalApplication {
  id: string
  organizationId: string
  submittedById: string | null
  submittedAt: string
  /**
   * `draft` exists only in this portal's local state: the organization is
   * registered (HC-051) but the application is not yet complete.
   */
  status: 'draft' | 'pending' | 'human_review' | 'approved' | 'rejected'
  documents: ApplicationDocument[]
  agreements: ApplicationAgreement[]
  /** Absent on applications that predate the profile (approved fixtures). */
  administrativeProfile?: AdministrativeProfile | null
  technicalQuestionnaire: TechnicalQuestionnaire | null
  reviewSteps: ReviewStep[]
  decisionId: string | null
}

export interface PortalNotification {
  id: string
  recipientId: string
  type: string
  title: string
  body: string
  createdAt: string
  read: boolean
  relatedId: string | null
}

/** Pages of the portal. Each onboarding page is delivered by its own ticket. */
export type StepId =
  | 'registration'
  | 'profile'
  | 'documents'
  | 'agreements'
  | 'technical'
  | 'dmi'
  | 'automated-review'
  | 'human-review'
  | 'decision'
  | 'node-configuration'
  | 'node-download'
  | 'node-installation'
  | 'node-status'

/**
 * Display state of one onboarding step, derived from fixtures.
 * `locked` means the step cannot start before a Governance decision, or can no
 * longer change after a rejection; `rejected` marks the rejected decision itself.
 */
export type StepStatus = 'completed' | 'attention' | 'in_progress' | 'pending' | 'locked' | 'rejected'

export interface OnboardingStep {
  id: StepId
  label: string
  ticket: string
  status: StepStatus
  /** Short French explanation of the status. */
  detail: string
}

/** A decision of the Governance / Ethics Authority, as published to the hospital (HC-059). */
export interface GovernanceDecision {
  id: string
  subjectType: 'hospital_application'
  subjectId: string
  outcome: 'approved' | 'rejected'
  decidedById: string
  decidedAt: string
  rationale: string
  conditions: string[]
  validUntil: string | null
  /** Set on decisions created by a demo scenario rather than read from the fixtures. */
  simulated?: boolean
}

export interface OnboardingSnapshot {
  organization: Organization
  manager: StaffMember
  /** `null` when the organization has not submitted an application yet. */
  application: HospitalApplication | null
  /** The Governance decision on the application, once published. */
  decision: GovernanceDecision | null
  steps: OnboardingStep[]
  notifications: PortalNotification[]
}
