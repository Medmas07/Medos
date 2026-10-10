import type { Organization, ResearchProject, ResearchSnapshot } from '../types/research'
import { editableDraft, withProject } from './projectCreation'
import { HEALTHCARE_ORGANIZATIONS } from './researchService'

/**
 * Participating hospitals selection (HC-096), MOCKED. The researcher picks the
 * federated organizations whose Hospital Node would run the analysis, from the
 * fictional fixtures; no Governance registry or Hospital Node is queried. The
 * selection is saved on the draft in the portal's session state only, after a
 * simulated delay. Selecting a hospital sends it nothing: the Governance /
 * Ethics Authority reviews the selection with the access request (HC-097) and
 * may authorize only part of it.
 */

/**
 * `eligible`: approved by Governance with an online Hospital Node.
 * `degraded`: approved, but its node is degraded or its DMI disconnected; it can
 * be selected, and its execution may fail until the node recovers.
 * `not_federated`: onboarding not approved or no Hospital Node; it cannot be selected.
 */
export type HospitalEligibility = 'eligible' | 'degraded' | 'not_federated'

export function hospitalEligibility(organization: Organization): HospitalEligibility {
  const { governanceStatus, node } = organization
  if (governanceStatus !== 'approved' || !node) return 'not_federated'
  return node.status === 'online' && node.dmiState === 'connected' ? 'eligible' : 'degraded'
}

export const isSelectable = (organization: Organization) => hospitalEligibility(organization) !== 'not_federated'

/** The form's values. */
export interface HospitalsDraft {
  organizationIds: string[]
}

export type HospitalsDraftErrors = Partial<Record<keyof HospitalsDraft, string>>

const byId = new Map(HEALTHCARE_ORGANIZATIONS.map((o) => [o.id, o]))

/** Validates a draft selection. Pure; returns French messages. */
export function validateHospitalsDraft(draft: HospitalsDraft): HospitalsDraftErrors {
  const ids = new Set(draft.organizationIds)
  if (ids.size === 0) return { organizationIds: 'Sélectionnez au moins un établissement.' }
  const organizations = [...ids].map((id) => byId.get(id))
  if (organizations.some((o) => o === undefined))
    return { organizationIds: "Un établissement ne fait pas partie de l'écosystème fédéré." }
  if (organizations.some((o) => !isSelectable(o!)))
    return { organizationIds: "Un établissement n'a pas encore de Hospital Node approuvé par la gouvernance." }
  return {}
}

/** The healthcare organizations of a selection, in directory order, without duplicates or unknown ids. Pure. */
export function selectedHospitals(ids: readonly string[]): Organization[] {
  return HEALTHCARE_ORGANIZATIONS.filter((o) => ids.includes(o.id))
}

/** The form's initial values for a project. Pure. */
export function draftFromProject(project: ResearchProject): HospitalsDraft {
  return { organizationIds: selectedHospitals(project.participatingOrganizationIds).map((o) => o.id) }
}

export type HospitalsStatus = 'selected' | 'missing'

export function hospitalsStatus(project: ResearchProject): HospitalsStatus {
  return project.participatingOrganizationIds.length > 0 ? 'selected' : 'missing'
}

export interface SaveOptions {
  /** Simulated network latency in milliseconds. */
  delayMs?: number
}

/**
 * Saves the participating hospitals on an editable draft, after a simulated
 * delay. Rejects an invalid selection or a project whose access request is submitted.
 */
export async function saveHospitals(
  snapshot: ResearchSnapshot,
  projectId: string,
  draft: HospitalsDraft,
  { delayMs = 400 }: SaveOptions = {},
): Promise<ResearchSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  const { project } = editableDraft(snapshot, projectId)
  if (Object.keys(validateHospitalsDraft(draft)).length > 0) {
    throw new Error('La sélection est incomplète : corrigez les champs signalés.')
  }
  return withProject(snapshot, {
    ...project,
    participatingOrganizationIds: selectedHospitals(draft.organizationIds).map((o) => o.id),
  })
}
