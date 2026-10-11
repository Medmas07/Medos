import organizationFixtures from '../../../../../demo-data/organizations.json'

/**
 * The fictional hospital this dashboard belongs to (canonical demo data,
 * ADR-0005). Every list in the portal is limited to this organization.
 */
export const HOSPITAL_ID = 'org-hospital-a'

/** Prefix of the hospital's local patient identifiers in the fixtures (`BEN-2024-08812`). */
export const LOCAL_ID_PREFIX = 'BEN'

const organization = organizationFixtures.organizations.find((o) => o.id === HOSPITAL_ID)
if (!organization) throw new Error(`Établissement ${HOSPITAL_ID} absent des données de démonstration.`)

export const HOSPITAL = {
  id: organization.id,
  name: organization.name,
  shortName: organization.shortName,
  city: organization.city,
}
