import type { GovernanceDecision, OnboardingSnapshot, TechnicalQuestionnaire } from '../types/onboarding'

/**
 * Hospital Node configuration summary (HC-060). Once the Governance / Ethics
 * Authority approves the application, the onboarding side derives the Node's
 * configuration. The file preview uses exactly the fields that the Hospital
 * Node loads and validates (`instances/hospital-node/infrastructure/config.py`,
 * HC-112). Generation is MOCKED: it is deterministic and runs in the browser.
 * The configuration holds no secret; Node identity and authentication are PLANNED.
 */

/** Federation contract `OpaqueRef` pattern, which the Hospital Node validates. */
export const OPAQUE_REF_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/

/** Fields accepted by the Hospital Node configuration loader (`_ConfigFile`, `extra="forbid"`). */
export const NODE_CONFIG_KEYS = [
  'notice',
  'node_ref',
  'organization_ref',
  'port',
  'storage_dir',
  'mock_clinical_records',
  'mock_access_grants',
  'mock_governance_decisions',
  'mock_medication_rules',
  'medication_rule_source',
  'ai_services_url',
] as const

export interface NodeConfigFile {
  notice: string
  node_ref: string
  organization_ref: string
  port: number | null
  storage_dir: string
  mock_clinical_records: string
  mock_access_grants: string
  mock_governance_decisions: string
  mock_medication_rules: string
  /** Fictional demo rules, or the validated ONC high-priority list (HC-163). */
  medication_rule_source: 'demo_fixture' | 'onc_high_priority_2012'
  /** AI Services URL for advisory warning explanations (HC-164); null keeps them off. */
  ai_services_url: string | null
}

/** Local ports suggested by ADR-0003; port 8103 is reserved for Hospital C. */
const RESERVED_PORTS: Record<string, number> = {
  'org-hospital-a': 8101,
  'org-hospital-b': 8102,
  'org-hospital-c': 8103,
}

/** Organizations with a fictional records file in `demo-data/records/`. */
const DEMO_RECORD_FILES: Record<string, string> = {
  'org-hospital-a': 'hospital-a.json',
  'org-hospital-b': 'hospital-b.json',
  'org-private-practice': 'private-practice.json',
}

export interface NodeConfigurationSummary {
  file: NodeConfigFile
  approvalDecisionRef: string
  /** Base URL the Federation node registry would record (HC-142), on the local demo host. */
  federationBaseUrl: string | null
  federationContractVersion: string
  environment: TechnicalQuestionnaire | null
  /** Points that must be resolved before the current Hospital Node can start with this file. */
  blockers: string[]
}

export type ConfigurationAvailability =
  | { kind: 'no_application' }
  | { kind: 'awaiting_decision' }
  | { kind: 'rejected'; decision: GovernanceDecision }
  | { kind: 'ready'; summary: NodeConfigurationSummary }

const slug = (organizationId: string) => organizationId.replace(/^org-/, '')

/** Derives the Node reference from the organization: `org-hospital-c` → `node-hospital-c`. Pure. */
export function nodeRefFor(organizationId: string): string {
  const ref = `node-${slug(organizationId)}`
  if (!OPAQUE_REF_PATTERN.test(ref)) throw new Error(`Référence de nœud invalide : ${ref}`)
  return ref
}

/** Builds the configuration summary of an approved application. Pure. */
export function nodeConfiguration(snapshot: OnboardingSnapshot): ConfigurationAvailability {
  const { application, decision, organization } = snapshot
  if (!application || application.status === 'draft') return { kind: 'no_application' }
  if (application.status === 'rejected' && decision) return { kind: 'rejected', decision }
  if (application.status !== 'approved' || decision?.outcome !== 'approved') return { kind: 'awaiting_decision' }

  const port = RESERVED_PORTS[organization.id] ?? null
  const recordFile = DEMO_RECORD_FILES[organization.id]
  const blockers: string[] = []
  if (port === null) blockers.push("Aucun port local n'est réservé pour cet établissement : il reste à définir.")
  if (!recordFile) {
    blockers.push(
      "Le Hospital Node actuel exige un fichier de dossiers fictifs (dépôt clinique simulé) ; il n'en existe pas pour cet établissement. Le nœud refuserait de démarrer tant que ce fichier n'est pas fourni.",
    )
  }

  return {
    kind: 'ready',
    summary: {
      file: {
        notice: `Configuration de démonstration générée après la décision ${decision.id}. Fictive ; ce n'est pas une configuration de production.`,
        node_ref: nodeRefFor(organization.id),
        organization_ref: organization.id,
        port,
        storage_dir: `../.storage/${slug(organization.id)}`,
        mock_clinical_records: `../../../demo-data/records/${recordFile ?? `${slug(organization.id)}.json`}`,
        mock_access_grants: '../../../demo-data/access.json',
        mock_governance_decisions: '../../../demo-data/governance.json',
        mock_medication_rules: '../../../demo-data/medication-rules.json',
        medication_rule_source: 'demo_fixture',
        ai_services_url: null,
      },
      approvalDecisionRef: decision.id,
      federationBaseUrl: port === null ? null : `http://localhost:${port}`,
      federationContractVersion: '1.0',
      environment: application.technicalQuestionnaire,
      blockers,
    },
  }
}

/** The file content as the Hospital Node would read it. Pure. */
export function configFileJson(file: NodeConfigFile): string {
  return JSON.stringify(file, NODE_CONFIG_KEYS as unknown as string[], 2)
}
