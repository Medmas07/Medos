import { journeyHref, SIGN_IN_HASH } from '../route'

// Absolute to the app root so a leftover `?demo=` scenario does not follow the visitor.
const BASE = import.meta.env.BASE_URL

/** "Télécharger l'instance pour hôpitaux": the onboarding forms, then the configuration guide and download. */
export const JOURNEY_START_HREF = `${BASE}${journeyHref('registration')}`

export const SIGN_IN_HREF = `${BASE}#${SIGN_IN_HASH}`
