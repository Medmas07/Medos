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

export interface ApplicationDocument {
  id: string
  title: string
  status: 'received' | 'missing' | 'rejected'
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
