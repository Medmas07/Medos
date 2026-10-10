import type { PopulationCriteria, ResearchProject, ResearchSnapshot } from '../types/research'
import { editableDraft, withProject } from './projectCreation'

/**
 * Research population definition (HC-094), MOCKED. The population is saved on
 * the draft in the portal's session state only, after a simulated delay: no
 * Research Service is called and no Hospital Node is queried, so no patient is
 * counted or selected. Defining a population requests no data access; it is
 * reviewed with the access request (HC-097).
 */

export const DESCRIPTION_MIN = 20
export const DESCRIPTION_MAX = 500
/** Age bounds accepted by the HC-180 execution contract. */
export const AGE_MAX = 130

/** The form's values, as typed. */
export interface PopulationDraft {
  description: string
  ageMin: string
  ageMax: string
  encounterFrom: string
  encounterTo: string
}

export type PopulationDraftErrors = Partial<Record<keyof PopulationDraft | 'criteria', string>>

const normalize = (text: string) => text.trim().replace(/\s+/g, ' ')

function parseAge(value: string): number | null | 'invalid' {
  const text = value.trim()
  if (!text) return null
  if (!/^\d{1,3}$/.test(text) || Number(text) > AGE_MAX) return 'invalid'
  return Number(text)
}

function parseDate(value: string): string | null | 'invalid' {
  const text = value.trim()
  if (!text) return null
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text)
  if (!match) return 'invalid'
  const date = new Date(`${text}T00:00:00Z`)
  // Rejects dates such as 2026-02-30, which Date would roll over.
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== text ? 'invalid' : text
}

/** Validates a draft population. Pure; returns French messages. */
export function validatePopulationDraft(draft: PopulationDraft): PopulationDraftErrors {
  const errors: PopulationDraftErrors = {}
  const description = normalize(draft.description)
  if (!description) errors.description = 'La description de la population est obligatoire.'
  else if (description.length < DESCRIPTION_MIN)
    errors.description = `La description doit compter au moins ${DESCRIPTION_MIN} caractères.`
  else if (description.length > DESCRIPTION_MAX)
    errors.description = `La description ne doit pas dépasser ${DESCRIPTION_MAX} caractères.`

  const ageMin = parseAge(draft.ageMin)
  const ageMax = parseAge(draft.ageMax)
  const invalidAge = `Indiquez un âge en années entières, de 0 à ${AGE_MAX}.`
  if (ageMin === 'invalid') errors.ageMin = invalidAge
  if (ageMax === 'invalid') errors.ageMax = invalidAge
  if (typeof ageMin === 'number' && typeof ageMax === 'number' && ageMin > ageMax)
    errors.ageMax = "L'âge maximal doit être supérieur ou égal à l'âge minimal."

  const from = parseDate(draft.encounterFrom)
  const to = parseDate(draft.encounterTo)
  if (from === 'invalid') errors.encounterFrom = 'Date invalide.'
  if (to === 'invalid') errors.encounterTo = 'Date invalide.'
  if (from && to && from !== 'invalid' && to !== 'invalid' && from > to)
    errors.encounterTo = 'La fin de la période doit suivre son début.'

  if ([ageMin, ageMax, from, to].every((value) => value === null))
    errors.criteria = "Indiquez au moins un critère : une tranche d'âge ou une période de consultation."

  return errors
}

/** The form's initial values for a project. Pure. */
export function draftFromProject(project: ResearchProject): PopulationDraft {
  const criteria = project.populationCriteria ?? {}
  return {
    description: project.population,
    ageMin: criteria.ageMin?.toString() ?? '',
    ageMax: criteria.ageMax?.toString() ?? '',
    encounterFrom: criteria.encounterFrom ?? '',
    encounterTo: criteria.encounterTo ?? '',
  }
}

/** The structured criteria of a valid draft, without the empty ones. Pure. */
export function criteriaFromDraft(draft: PopulationDraft): PopulationCriteria {
  const age = (value: string) => (value.trim() ? Number(value.trim()) : undefined)
  const date = (value: string) => value.trim() || undefined
  const criteria: PopulationCriteria = {
    ageMin: age(draft.ageMin),
    ageMax: age(draft.ageMax),
    encounterFrom: date(draft.encounterFrom),
    encounterTo: date(draft.encounterTo),
  }
  return Object.fromEntries(Object.entries(criteria).filter(([, value]) => value !== undefined))
}

/**
 * `defined` when structured criteria are set, `described` for a fixture project
 * that only has a description, `missing` otherwise.
 */
export type PopulationStatus = 'defined' | 'described' | 'missing'

export function populationStatus(project: ResearchProject): PopulationStatus {
  if (project.populationCriteria) return 'defined'
  return project.population.trim() ? 'described' : 'missing'
}

export interface SaveOptions {
  /** Simulated network latency in milliseconds. */
  delayMs?: number
}

/**
 * Saves the population on an editable draft, after a simulated delay. Rejects
 * an invalid draft or a project whose access request is submitted.
 */
export async function savePopulation(
  snapshot: ResearchSnapshot,
  projectId: string,
  draft: PopulationDraft,
  { delayMs = 400 }: SaveOptions = {},
): Promise<ResearchSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  const { project } = editableDraft(snapshot, projectId)
  if (Object.keys(validatePopulationDraft(draft)).length > 0) {
    throw new Error('La population est incomplète : corrigez les champs signalés.')
  }
  return withProject(snapshot, {
    ...project,
    population: normalize(draft.description),
    populationCriteria: criteriaFromDraft(draft),
  })
}
