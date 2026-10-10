import type { ResearchProject, ResearchSnapshot } from '../types/research'
import { editableDraft, withProject } from './projectCreation'

/**
 * Requested variables definition (HC-095), MOCKED. The researcher picks
 * variables from a fictional demo catalog; no Hospital Node data dictionary is
 * queried, so whether a node actually holds a variable is not checked. The
 * selection is saved on the draft in the portal's session state only, after a
 * simulated delay. Requesting variables gives access to no data; they are
 * reviewed with the access request (HC-097).
 */

export const MAX_VARIABLES = 10
export const JUSTIFICATION_MIN = 20
export const JUSTIFICATION_MAX = 500

export type VariableCategory = 'demographics' | 'encounters' | 'conditions' | 'measurements'

export interface CatalogVariable {
  /** Name a Hospital Node receives, `DataScope.variables` of the HC-180 execution contract. */
  name: string
  /** French label, as fixture projects and the Governance review show it. */
  label: string
  category: VariableCategory
  description: string
  /** Combined with others, it may help re-identify a person; output checks still apply. */
  quasiIdentifier?: boolean
}

export const CATEGORY_LABELS: Record<VariableCategory, string> = {
  demographics: 'Démographie',
  encounters: 'Parcours de soins',
  conditions: 'Pathologies et traitements',
  measurements: 'Mesures et examens',
}

/**
 * Fictional demo catalog. Only derived or coarsened variables are offered:
 * direct identifiers (name, exact birth date, address, record number) cannot
 * be requested.
 */
export const VARIABLE_CATALOG: readonly CatalogVariable[] = [
  { name: 'age_band', label: "Tranche d'âge", category: 'demographics', description: 'Âge par tranche de 10 ans, jamais la date de naissance.', quasiIdentifier: true },
  { name: 'sex', label: 'Sexe', category: 'demographics', description: 'Sexe administratif.', quasiIdentifier: true },
  { name: 'governorate', label: 'Gouvernorat de résidence', category: 'demographics', description: "Gouvernorat seulement, jamais l'adresse.", quasiIdentifier: true },
  { name: 'encounter_month', label: 'Mois de consultation', category: 'encounters', description: 'Mois et année de chaque consultation.' },
  { name: 'emergency_visit', label: 'Passage aux urgences', category: 'encounters', description: 'Au moins un passage aux urgences sur la période.' },
  { name: 'hospital_admission', label: 'Hospitalisation', category: 'encounters', description: 'Au moins une hospitalisation sur la période.' },
  { name: 'type_2_diabetes', label: 'Diabète de type 2', category: 'conditions', description: 'Diagnostic de diabète de type 2 enregistré.' },
  { name: 'treated_hypertension', label: 'Hypertension traitée', category: 'conditions', description: 'Hypertension avec au moins un traitement prescrit.' },
  { name: 'asthma', label: 'Asthme', category: 'conditions', description: "Diagnostic d'asthme enregistré." },
  { name: 'hba1c', label: 'HbA1c', category: 'measurements', description: 'Dernière hémoglobine glyquée de la période, en %.' },
  { name: 'ldl_cholesterol', label: 'LDL-cholestérol', category: 'measurements', description: 'Dernier LDL-cholestérol de la période, en g/L.' },
  { name: 'bmi_band', label: "Classe d'IMC", category: 'measurements', description: "Classe d'indice de masse corporelle (OMS)." },
]

const byName = new Map(VARIABLE_CATALOG.map((v) => [v.name, v]))
const byLabel = new Map(VARIABLE_CATALOG.map((v) => [v.label, v]))

/** The form's values. */
export interface VariablesDraft {
  /** Contract names of the selected catalog variables. */
  names: string[]
  justification: string
}

export type VariablesDraftErrors = Partial<Record<keyof VariablesDraft, string>>

const normalize = (text: string) => text.trim().replace(/\s+/g, ' ')

/** Validates a draft selection. Pure; returns French messages. */
export function validateVariablesDraft(draft: VariablesDraft): VariablesDraftErrors {
  const errors: VariablesDraftErrors = {}
  const names = new Set(draft.names)
  if (names.size === 0) errors.names = 'Sélectionnez au moins une variable.'
  else if ([...names].some((name) => !byName.has(name))) errors.names = 'Une variable ne fait pas partie du catalogue.'
  else if (names.size > MAX_VARIABLES)
    errors.names = `Sélectionnez au plus ${MAX_VARIABLES} variables : ne demandez que le nécessaire.`

  const justification = normalize(draft.justification)
  if (!justification) errors.justification = 'La justification est obligatoire.'
  else if (justification.length < JUSTIFICATION_MIN)
    errors.justification = `La justification doit compter au moins ${JUSTIFICATION_MIN} caractères.`
  else if (justification.length > JUSTIFICATION_MAX)
    errors.justification = `La justification ne doit pas dépasser ${JUSTIFICATION_MAX} caractères.`

  return errors
}

/** The catalog entries of a selection, in catalog order, without duplicates or unknown names. Pure. */
export function catalogEntries(names: readonly string[]): CatalogVariable[] {
  return VARIABLE_CATALOG.filter((v) => names.includes(v.name))
}

/**
 * The project's requested variables matched to the catalog: by contract name
 * when set in this portal, by label for a fixture project. `unmatched` keeps
 * fixture labels the catalog does not know.
 */
export function requestedVariables(project: ResearchProject): { entries: CatalogVariable[]; unmatched: string[] } {
  if (project.variableNames) return { entries: catalogEntries(project.variableNames), unmatched: [] }
  const entries = project.variables.map((label) => byLabel.get(label))
  return {
    entries: entries.filter((v): v is CatalogVariable => v !== undefined),
    unmatched: project.variables.filter((_, i) => entries[i] === undefined),
  }
}

/** The form's initial values for a project. Pure. */
export function draftFromProject(project: ResearchProject): VariablesDraft {
  return {
    names: requestedVariables(project).entries.map((v) => v.name),
    justification: project.variablesJustification ?? '',
  }
}

/**
 * `justified` when selected in this portal with a justification, `listed` for a
 * fixture project that only has variable labels, `missing` otherwise.
 */
export type VariablesStatus = 'justified' | 'listed' | 'missing'

export function variablesStatus(project: ResearchProject): VariablesStatus {
  if (project.variableNames && project.variablesJustification) return 'justified'
  return project.variables.length > 0 ? 'listed' : 'missing'
}

export interface SaveOptions {
  /** Simulated network latency in milliseconds. */
  delayMs?: number
}

/**
 * Saves the requested variables on an editable draft, after a simulated delay.
 * Rejects an invalid selection or a project whose access request is submitted.
 */
export async function saveVariables(
  snapshot: ResearchSnapshot,
  projectId: string,
  draft: VariablesDraft,
  { delayMs = 400 }: SaveOptions = {},
): Promise<ResearchSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  const { project } = editableDraft(snapshot, projectId)
  if (Object.keys(validateVariablesDraft(draft)).length > 0) {
    throw new Error('La sélection est incomplète : corrigez les champs signalés.')
  }
  const entries = catalogEntries(draft.names)
  return withProject(snapshot, {
    ...project,
    variables: entries.map((v) => v.label),
    variableNames: entries.map((v) => v.name),
    variablesJustification: normalize(draft.justification),
  })
}
