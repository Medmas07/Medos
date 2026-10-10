import { describe, expect, it, beforeEach } from 'vitest'
import {
  authService,
  CANONICAL_DEMO_IDENTITIES,
  ROLE_SCOPES,
} from '../src/services/authService'

describe('HC-210 Demo Authentication Flow (authService)', () => {
  const FIXED_NOW = new Date('2026-10-10T10:00:00+01:00')

  beforeEach(() => {
    // Reset to default nominal session before each test
    authService.login('usr-olfa', { scenario: 'nominal', now: FIXED_NOW })
  })

  it('lists all canonical fictional demo identities with roles and orgs', () => {
    const identities = authService.getIdentities()
    expect(identities.length).toBe(CANONICAL_DEMO_IDENTITIES.length)

    const ids = identities.map((i) => i.id)
    expect(ids).toContain('usr-olfa')
    expect(ids).toContain('usr-mehdi')
    expect(ids).toContain('usr-aymen')
    expect(ids).toContain('clin-x')
    expect(ids).toContain('pat-a')
    expect(ids).toContain('rel-sami')

    const olfa = authService.getIdentity('usr-olfa')
    expect(olfa).toBeDefined()
    expect(olfa?.role).toBe('governance_reviewer')
    expect(olfa?.organizationId).toBe('org-governance')
  })

  it('provides role scopes according to declared responsibilities', () => {
    expect(ROLE_SCOPES.governance_reviewer).toContain('governance:review')
    expect(ROLE_SCOPES.hospital_manager).toContain('hospital:onboarding')
    expect(ROLE_SCOPES.researcher).toContain('research:compute-to-data')
    expect(ROLE_SCOPES.physician).toContain('clinical:alerts')
    expect(ROLE_SCOPES.patient).toContain('patient:consent')
  })

  it('establishes a nominal active demo session', () => {
    const res = authService.login('usr-olfa', {
      scenario: 'nominal',
      now: FIXED_NOW,
    })

    expect(res.kind).toBe('success')
    if (res.kind !== 'success') return

    expect(res.session.status).toBe('active')
    expect(res.session.depth).toBe('D1')
    expect(res.session.fictional).toBe(true)
    expect(res.session.identity.id).toBe('usr-olfa')
    expect(res.session.sessionToken).toContain('demo-token-usr-olfa-nominal')
    expect(res.session.scopes).toEqual(ROLE_SCOPES.governance_reviewer)
    expect(res.session.demoNotice).toContain('AUTHENTIFICATION DÉMO D1')
    expect(new Date(res.session.expiresAt).getTime()).toBeGreaterThan(FIXED_NOW.getTime())
  })

  it('establishes an expired demo session (401 simulation)', () => {
    const res = authService.login('usr-olfa', {
      scenario: 'expired',
      now: FIXED_NOW,
    })

    expect(res.kind).toBe('success')
    if (res.kind !== 'success') return

    expect(res.session.status).toBe('expired')
    expect(res.session.demoNotice).toContain('401')
    expect(new Date(res.session.expiresAt).getTime()).toBeLessThan(FIXED_NOW.getTime())
  })

  it('handles invalid credentials scenario gracefully', () => {
    const res = authService.login('usr-olfa', {
      scenario: 'invalid_credentials',
      now: FIXED_NOW,
    })

    expect(res.kind).toBe('error')
    if (res.kind !== 'error') return

    expect(res.code).toBe('INVALID_CREDENTIALS')
    expect(res.message).toContain('Échec de connexion simulé')
  })

  it('rejects unknown identity IDs', () => {
    const res = authService.login('usr-unknown', {
      scenario: 'nominal',
      now: FIXED_NOW,
    })

    expect(res.kind).toBe('error')
    if (res.kind !== 'error') return

    expect(res.code).toBe('IDENTITY_NOT_FOUND')
  })

  it('evaluates authorization correctly for Governance Portal', () => {
    // Reviewer active session -> authorized
    const activeReviewer = authService.getCurrentSession()
    expect(authService.isAuthorizedForGovernance(activeReviewer)).toBe(true)

    // Other roles -> unauthorized for Governance Portal
    const managerLogin = authService.login('usr-mehdi', { scenario: 'nominal', now: FIXED_NOW })
    expect(managerLogin.kind).toBe('success')
    expect(authService.isAuthorizedForGovernance(authService.getCurrentSession())).toBe(false)

    const patientLogin = authService.login('pat-a', { scenario: 'nominal', now: FIXED_NOW })
    expect(patientLogin.kind).toBe('success')
    expect(authService.isAuthorizedForGovernance(authService.getCurrentSession())).toBe(false)

    // Expired reviewer session -> unauthorized
    const expiredReviewer = authService.login('usr-olfa', { scenario: 'expired', now: FIXED_NOW })
    expect(expiredReviewer.kind).toBe('success')
    expect(authService.isAuthorizedForGovernance(authService.getCurrentSession())).toBe(false)

    // Null session -> unauthorized
    authService.logout()
    expect(authService.isAuthorizedForGovernance(null)).toBe(false)
  })

  it('notifies subscribers on session changes', () => {
    let callCount = 0
    const unsubscribe = authService.subscribe(() => {
      callCount++
    })

    authService.login('usr-mehdi', { scenario: 'nominal', now: FIXED_NOW })
    expect(callCount).toBe(1)

    authService.logout()
    expect(callCount).toBe(2)
    expect(authService.getCurrentSession()).toBeNull()

    unsubscribe()
    authService.login('usr-olfa', { scenario: 'nominal', now: FIXED_NOW })
    expect(callCount).toBe(2)
  })
})
