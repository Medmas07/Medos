import { STEP_DEFINITIONS } from './services/onboardingService'
import type { StepId } from './types/onboarding'

/**
 * Hash routes:
 * - no hash or an in-page anchor: the MedOS landing page;
 * - `#connexion`: the sign-in page (authentication not implemented);
 * - `#adhesion` or `#adhesion/<step>`: the guided journey ending with the Hospital Node download.
 */
export type Route = { kind: 'landing' } | { kind: 'signin' } | { kind: 'journey'; step: StepId }

export const JOURNEY_PREFIX = 'adhesion'
export const SIGN_IN_HASH = 'connexion'

const STEP_IDS: readonly string[] = STEP_DEFINITIONS.map((d) => d.id)

export function routeFromHash(hash: string): Route {
  const value = hash.replace(/^#/, '')
  if (value === SIGN_IN_HASH) return { kind: 'signin' }
  if (value === JOURNEY_PREFIX || value.startsWith(`${JOURNEY_PREFIX}/`)) {
    const step = value.slice(JOURNEY_PREFIX.length + 1)
    return { kind: 'journey', step: STEP_IDS.includes(step) ? (step as StepId) : 'registration' }
  }
  return { kind: 'landing' }
}

export function journeyHref(step: StepId = 'registration'): string {
  return `#${JOURNEY_PREFIX}/${step}`
}
