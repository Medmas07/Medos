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
  /** Governance onboarding status, displayed only; `null` for non-healthcare organizations. */
  governanceStatus?: 'approved' | 'under_review' | 'rejected' | null
  /** The organization's Hospital Node, once federated. */
  node?: HospitalNodeSummary | null
}

/** A Hospital Node's state as fixtures describe it (HC-005); the portal never contacts it. */
export interface HospitalNodeSummary {
  /** Node reference, `node_ref` of the HC-180 execution contract. */
  id: string
  status: 'online' | 'degraded' | 'offline'
  dmiState: 'connected' | 'disconnected'
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
  /** Plain-language description of the studied population, read by the Governance review. */
  population: string
  /** Structured eligibility criteria set in this portal (HC-094); absent on fixture projects. */
  populationCriteria?: PopulationCriteria
  /** French labels of the requested variables, read by the Governance review. */
  variables: string[]
  /**
   * Names of the requested variables, `DataScope.variables` of the HC-180
   * execution contract, in the order of `variables`. Set in this portal
   * (HC-095); absent on fixture projects.
   */
  variableNames?: string[]
  /** Why each requested variable is needed (HC-095); absent on fixture projects. */
  variablesJustification?: string
  /**
   * Organizations whose Hospital Node is asked to run the analysis,
   * `target_organizations` of the HC-182 job contract (HC-096).
   */
  participatingOrganizationIds: string[]
  protocolDocument: ProjectDocumentRef | null
  /** Optional supporting documents; absent on fixture projects. */
  supportingDocuments?: ProjectDocumentRef[]
  researchAccessRequestId: string | null
}

/**
 * Eligibility criteria of a research population (HC-094). They mirror the
 * criteria a Hospital Node can apply, `DataScope.population` of the HC-180
 * execution contract; at least one is set. Ages are in completed years,
 * dates are `YYYY-MM-DD`, and every bound is inclusive.
 */
export interface PopulationCriteria {
  ageMin?: number
  ageMax?: number
  encounterFrom?: string
  encounterTo?: string
}

/** Metadata of a file deposited in this portal (HC-093); its content is never read. */
export interface DocumentUpload {
  fileName: string
  sizeBytes: number
  mediaType: string
  uploadedAt: string
}

export type ProjectDocumentType = 'protocol' | 'data_management_plan' | 'information_notice'

export interface ProjectDocumentRef {
  id: string
  title: string
  /** Set for a supporting document; the protocol is `protocolDocument`. */
  type?: Exclude<ProjectDocumentType, 'protocol'>
  /** Only set for a document deposited in this portal (session state). */
  upload?: DocumentUpload
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

export interface ComputeJobStage {
  id: string
  stage: 'authorization_check' | 'execution' | 'aggregation' | 'output_validation'
  organizationId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  completedAt?: string
}

export interface ComputeJob {
  id: string
  projectId: string
  authorizationDecisionId: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  submittedAt: string
  stages: ComputeJobStage[]
  controlledResultId: string | null
}

/** A controlled result's release metadata; its aggregate rows belong to the result panel (HC-101). */
export interface ControlledResultSummary {
  id: string
  jobId: string
  title: string
  minimumCellSize: number
  disclosureCheck: 'passed' | 'failed'
  provenance: string
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
  /** Reference time the snapshot was derived at (ISO 8601). */
  asOf: string
  researcher: StaffMember
  organization: Organization
  projects: ProjectSummary[]
  jobs: ComputeJob[]
  results: ControlledResultSummary[]
  pages: PortalPage[]
  notifications: PortalNotification[]
}
