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

export interface ApplicationAgreement {
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
 * `locked` means the step cannot start before a Governance decision.
 */
export type StepStatus = 'completed' | 'attention' | 'in_progress' | 'pending' | 'locked'

export interface OnboardingStep {
  id: StepId
  label: string
  ticket: string
  status: StepStatus
  /** Short French explanation of the status. */
  detail: string
}

export interface OnboardingSnapshot {
  organization: Organization
  manager: StaffMember
  /** `null` when the organization has not submitted an application yet. */
  application: HospitalApplication | null
  steps: OnboardingStep[]
  notifications: PortalNotification[]
}
