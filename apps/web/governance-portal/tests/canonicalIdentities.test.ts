import { describe, expect, it } from 'vitest'
import organizationsFixtures from '../../../../demo-data/organizations.json'
import peopleFixtures from '../../../../demo-data/people.json'
import { CANONICAL_DEMO_IDENTITIES } from '../src/services/authService'

// HC-240: the demo sign-in personas are the HC-005 cast, at their own organizations.
describe('HC-240 canonical demo identities', () => {
  const people = [
    ...peopleFixtures.patients,
    ...peopleFixtures.relatives,
    ...peopleFixtures.clinicians,
    ...peopleFixtures.staff,
  ] as { id: string; firstName: string; lastName: string; title?: string | null; organizationId?: string }[]
  const organizations = new Map(organizationsFixtures.organizations.map((o) => [o.id, o]))

  it.each(CANONICAL_DEMO_IDENTITIES.map((identity) => [identity.id, identity]))(
    '%s is a canonical person',
    (_, identity) => {
      const person = people.find((p) => p.id === identity.id)
      expect(person, identity.id).toBeDefined()
      expect(identity.displayName).toBe(
        [person!.title, person!.firstName, person!.lastName].filter(Boolean).join(' '),
      )
      expect(identity.organizationName).toBe(organizations.get(identity.organizationId)?.name)
      if (person!.organizationId) expect(identity.organizationId).toBe(person!.organizationId)
    },
  )

  it('names only fictional HC-005 organizations', () => {
    const names = new Set(organizationsFixtures.organizations.map((o) => o.name))
    for (const identity of CANONICAL_DEMO_IDENTITIES) expect(names).toContain(identity.organizationName)
  })
})
