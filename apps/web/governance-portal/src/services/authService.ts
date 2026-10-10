/**
 * HC-210: Demo authentication flow service at initial depth D1.
 *
 * Implements deterministic demo identities and sessions according to
 * contracts/api/auth/demo-authentication.v1.yaml.
 *
 * Explicit D1 non-production boundary:
 * - Deterministic personas from canonical demo fixtures (HC-005).
 * - Simulated tokens, mock expiration, and scenario-based review states.
 * - In-memory reactive session store with subscribe/getSnapshot pattern.
 * - Explicit role-to-portal authorization checks with friendly 401/403 states.
 */

export type DemoRole =
  | 'governance_reviewer'
  | 'hospital_manager'
  | 'researcher'
  | 'physician'
  | 'nurse'
  | 'patient'
  | 'relative'

export interface DemoIdentity {
  id: string
  displayName: string
  title?: string
  role: DemoRole
  organizationId: string
  organizationName: string
  description: string
  defaultPortal: 'governance-portal' | 'hospital-portal' | 'research-portal' | 'clinician-app' | 'patient-app'
}

export type DemoAuthScenario = 'nominal' | 'expired' | 'invalid_credentials'

export interface DemoSession {
  sessionId: string
  sessionToken: string
  status: 'active' | 'expired' | 'revoked'
  createdAt: string
  expiresAt: string
  identity: DemoIdentity
  scopes: string[]
  depth: 'D1'
  fictional: true
  demoNotice: string
}

export type AuthResult =
  | { kind: 'success'; session: DemoSession }
  | { kind: 'error'; code: 'INVALID_CREDENTIALS' | 'IDENTITY_NOT_FOUND' | 'EXPIRED_SESSION'; message: string }

export const CANONICAL_DEMO_IDENTITIES: readonly DemoIdentity[] = [
  {
    id: 'usr-olfa',
    displayName: 'Pr Olfa Hamdi',
    title: 'Pr',
    role: 'governance_reviewer',
    organizationId: 'org-governance',
    organizationName: "Autorité de Gouvernance et d'Éthique",
    description: "Réviseure de gouvernance habilitée à évaluer les adhésions et demandes d'accès",
    defaultPortal: 'governance-portal',
  },
  {
    id: 'usr-mehdi',
    displayName: 'Mehdi Sassi',
    role: 'hospital_manager',
    organizationId: 'org-hospital-c',
    organizationName: 'Hôpital Universitaire C (La Rabta)',
    description: "Responsable d'établissement hospitalier en cours d'adhésion",
    defaultPortal: 'hospital-portal',
  },
  {
    id: 'usr-aymen',
    displayName: 'Dr Aymen Rezgui',
    title: 'Dr',
    role: 'researcher',
    organizationId: 'org-research-lab',
    organizationName: 'Laboratoire de Recherche Médicale',
    description: "Chercheur principal soumettant des projets d'accès aux données",
    defaultPortal: 'research-portal',
  },
  {
    id: 'clin-x',
    displayName: 'Dr Youssef Gharbi',
    title: 'Dr',
    role: 'physician',
    organizationId: 'org-hospital-a',
    organizationName: 'Hôpital Universitaire A (Charles Nicolle)',
    description: 'Praticien cardiologue traitant recevant des alertes cliniques',
    defaultPortal: 'clinician-app',
  },
  {
    id: 'pat-a',
    displayName: 'Leïla Mansouri',
    role: 'patient',
    organizationId: 'org-hospital-a',
    organizationName: 'Hôpital Universitaire A (Charles Nicolle)',
    description: 'Patiente titulaire consultant son dossier et gérant ses consentements',
    defaultPortal: 'patient-app',
  },
  {
    id: 'rel-sami',
    displayName: 'Sami Mansouri',
    role: 'relative',
    organizationId: 'org-hospital-a',
    organizationName: 'Hôpital Universitaire A (Charles Nicolle)',
    description: 'Fils et proche délégué de la patiente Leïla Mansouri',
    defaultPortal: 'patient-app',
  },
] as const

export const ROLE_SCOPES: Record<DemoRole, string[]> = {
  governance_reviewer: ['governance:review', 'governance:audit', 'governance:policy'],
  hospital_manager: ['hospital:onboarding', 'hospital:node-admin'],
  researcher: ['research:projects', 'research:requests', 'research:compute-to-data'],
  physician: ['clinical:consultations', 'clinical:alerts'],
  nurse: ['clinical:intake'],
  patient: ['patient:records', 'patient:consent'],
  relative: ['patient:delegate-view'],
}

const DEFAULT_DEMO_IDENTITY = CANONICAL_DEMO_IDENTITIES[0] // Pr Olfa Hamdi

const EIGHT_HOURS_MS = 8 * 60 * 60 * 1000

function createDefaultSession(now = new Date()): DemoSession {
  return {
    sessionId: `sess-demo-${DEFAULT_DEMO_IDENTITY.id}-nominal`,
    sessionToken: `demo-token-${DEFAULT_DEMO_IDENTITY.id}-active`,
    status: 'active',
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + EIGHT_HOURS_MS).toISOString(),
    identity: DEFAULT_DEMO_IDENTITY,
    scopes: ROLE_SCOPES[DEFAULT_DEMO_IDENTITY.role],
    depth: 'D1',
    fictional: true,
    demoNotice: 'AUTHENTIFICATION DÉMO D1 — Simulation déterministe. Non sécurisée pour la production.',
  }
}

class DemoAuthService {
  private currentSession: DemoSession | null = createDefaultSession()
  private listeners = new Set<() => void>()

  getIdentities(): readonly DemoIdentity[] {
    return CANONICAL_DEMO_IDENTITIES
  }

  getIdentity(id: string): DemoIdentity | undefined {
    return CANONICAL_DEMO_IDENTITIES.find((i) => i.id === id)
  }

  getCurrentSession(): DemoSession | null {
    return this.currentSession
  }

  login(
    identityId: string,
    options: {
      scenario?: DemoAuthScenario
      password?: string
      now?: Date
    } = {},
  ): AuthResult {
    const identity = this.getIdentity(identityId)
    if (!identity) {
      return {
        kind: 'error',
        code: 'IDENTITY_NOT_FOUND',
        message: `Identité démo '${identityId}' introuvable dans les données canoniques.`,
      }
    }

    const scenario = options.scenario ?? 'nominal'
    const now = options.now ?? new Date()

    if (scenario === 'invalid_credentials') {
      return {
        kind: 'error',
        code: 'INVALID_CREDENTIALS',
        message: 'Échec de connexion simulé : mot de passe ou identifiants démo incorrects.',
      }
    }

    const isExpired = scenario === 'expired'
    const expiresAt = isExpired
      ? new Date(now.getTime() - 60 * 1000).toISOString()
      : new Date(now.getTime() + EIGHT_HOURS_MS).toISOString()

    const session: DemoSession = {
      sessionId: `sess-demo-${identity.id}-${scenario}-${Date.now().toString(36)}`,
      sessionToken: `demo-token-${identity.id}-${scenario}`,
      status: isExpired ? 'expired' : 'active',
      createdAt: now.toISOString(),
      expiresAt,
      identity,
      scopes: ROLE_SCOPES[identity.role] ?? [],
      depth: 'D1',
      fictional: true,
      demoNotice: isExpired
        ? 'SESSION DÉMO EXPIRÉE (D1) — Simulation du code HTTP 401.'
        : 'AUTHENTIFICATION DÉMO D1 — Simulation déterministe. Non sécurisée pour la production.',
    }

    this.currentSession = session
    this.notify()
    return { kind: 'success', session }
  }

  logout(): void {
    this.currentSession = null
    this.notify()
  }

  isAuthorizedForGovernance(session: DemoSession | null): boolean {
    if (!session || session.status !== 'active') return false
    return session.identity.role === 'governance_reviewer'
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  getSnapshot = (): DemoSession | null => {
    return this.currentSession
  }

  private notify() {
    this.listeners.forEach((listener) => listener())
  }
}

export const authService = new DemoAuthService()
