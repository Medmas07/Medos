/**
 * Types for the Research Portal shell.
 * They mirror the canonical fictional fixtures in demo-data/ (HC-005); they are
 * not API contracts. Research Service and research-job contracts are PLANNED.
 */

export interface Organization {
  id: string
  type: string
  name: string
  shortName: string
  city: string
}

export interface StaffMember {
  id: string
  title?: string
  firstName: string
  lastName: string
  role: string
  organizationId: string
}

export interface ResearchProject {
  id: string
  title: string
  principalInvestigatorId: string
  organizationId: string
  status: 'draft' | 'under_review' | 'approved' | 'rejected'
  createdAt: string
  summary: string
  population: string
  variables: string[]
  participatingOrganizationIds: string[]
  protocolDocument: { id: string; title: string } | null
  researchAccessRequestId: string | null
}

export interface ResearchAccessRequest {
  id: string
  projectId: string
  submittedById: string
  submittedAt: string
  status: 'under_review' | 'approved' | 'rejected'
  decisionId: string | null
}

/** A Governance decision, displayed only: the portal cannot record one. */
export interface GovernanceDecision {
  id: string
  subjectType: string
  subjectId: string
  outcome: 'approved' | 'rejected'
  decidedById: string
  decidedAt: string
  rationale: string
  conditions: string[]
  validUntil: string | null
}

export interface ComputeJob {
  id: string
  projectId: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  submittedAt: string
  controlledResultId: string | null
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

/** A research project joined with its access request, Governance decision, and hospitals. */
export interface ProjectSummary {
  project: ResearchProject
  request: ResearchAccessRequest | null
  decision: GovernanceDecision | null
  participatingOrganizations: Organization[]
  /** Whether a still-valid Governance approval allows Compute-to-Data, at load time. */
  authorized: boolean
}

/** Pages of the portal. Each page is delivered by its own ticket. */
export type PageId =
  | 'dashboard'
  | 'new-project'
  | 'protocol'
  | 'population'
  | 'variables'
  | 'hospitals'
  | 'submit-request'
  | 'request-status'
  | 'workspace'
  | 'execution'
  | 'results'
  | 'sciagents'

/**
 * Availability of a page for the signed-in researcher, derived from fixtures.
 * `locked` means the page needs a Governance authorization that does not exist yet.
 */
export type PageStatus = 'available' | 'locked'

export interface PortalPage {
  id: PageId
  label: string
  ticket: string
  status: PageStatus
  /** Short French explanation of what the fixtures hold for this page. */
  detail: string
}

export interface ResearchSnapshot {
  researcher: StaffMember
  organization: Organization
  projects: ProjectSummary[]
  jobs: ComputeJob[]
  pages: PortalPage[]
  notifications: PortalNotification[]
}
