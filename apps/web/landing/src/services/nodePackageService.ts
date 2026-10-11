import type { NodePackageRecord, OnboardingSnapshot } from '../types/onboarding'
import { hasDmiAnswers } from './dmiService'
import { nodeConfiguration, NODE_CONFIG_KEYS, type NodeConfigFile } from './nodeConfigService'
import { deriveSteps } from './onboardingService'

/**
 * Hospital Node demo package (HC-061). After approval, the hospital downloads a
 * package for its Node. At D1 the package is a single JSON manifest built in the
 * browser: it carries the Node configuration (HC-060) and the inputs the Node
 * will need, and states openly what a real package would add and why it is
 * absent. It contains no executable and no secret, and installs nothing. Node
 * secrets are generated locally at installation, never by this portal.
 */

export const PACKAGE_FORMAT_VERSION = '0.1-demo'

export interface PackageItem {
  item: 'containerImages' | 'nodeIdentity' | 'installationHelper'
  /** `installation_package`: delivered in the HC-221 installation package, not in this manifest. */
  status: 'open' | 'planned' | 'installation_package'
  note: string
}

/** What the product vision lists in a package but this demo manifest does not hold. */
export const NOT_INCLUDED: readonly PackageItem[] = [
  {
    item: 'containerImages',
    status: 'installation_package',
    note: "L'image du Hospital Node (HC-220) est livrée dans le package d'installation que l'opérateur de la plateforme construit après vérification de l'approbation par le Governance Node (HC-221), pas dans ce manifeste de démonstration.",
  },
  {
    item: 'nodeIdentity',
    status: 'planned',
    note: "Identité et secrets du nœud générés localement lors de l'installation ; jamais transmis par le portail.",
  },
  {
    item: 'installationHelper',
    status: 'installation_package',
    note: "L'assistant d'installation est livré dans le package d'installation (HC-221) : il vérifie le package et vos données, puis démarre le nœud, sans jamais installer de logiciel.",
  },
]

export interface PackageManifest {
  fictional: true
  notice: string
  packageFormatVersion: string
  generatedAt: string
  node: { nodeRef: string; organizationRef: string; approvalDecisionRef: string }
  hospitalNodeConfig: NodeConfigFile
  deploymentEnvironment: { hostingType: string; operatingSystem: string; containerRuntimeAvailable: boolean } | null
  dmiAdapter: { status: 'planned'; dmiSystem: string; integrationMethods: string[]; note: string } | null
  notIncluded: readonly PackageItem[]
  knownLimitations: string[]
}

export interface PreparedPackage {
  fileName: string
  json: string
  sha256: string
  sizeBytes: number
  generatedAt: string
}

/** Builds the manifest of an approved application, or `null` before approval. Pure. */
export function buildManifest(snapshot: OnboardingSnapshot, generatedAt: string): PackageManifest | null {
  const availability = nodeConfiguration(snapshot)
  if (availability.kind !== 'ready') return null
  const { summary } = availability
  const q = summary.environment
  const config = Object.fromEntries(NODE_CONFIG_KEYS.map((key) => [key, summary.file[key]])) as unknown as NodeConfigFile
  return {
    fictional: true,
    notice:
      "Package de démonstration du Hospital Node. Fictif : aucun exécutable, aucun secret, aucune donnée patient. Ce n'est pas un package de production.",
    packageFormatVersion: PACKAGE_FORMAT_VERSION,
    generatedAt,
    node: {
      nodeRef: summary.file.node_ref,
      organizationRef: summary.file.organization_ref,
      approvalDecisionRef: summary.approvalDecisionRef,
    },
    hospitalNodeConfig: config,
    deploymentEnvironment: q
      ? { hostingType: q.hostingType, operatingSystem: q.operatingSystem, containerRuntimeAvailable: q.containerRuntimeAvailable }
      : null,
    dmiAdapter:
      q && hasDmiAnswers(q)
        ? {
            status: 'planned',
            dmiSystem: q.dmiSystem!,
            integrationMethods: [...(q.integrationMethods ?? [])],
            note: "L'adaptateur DMI est configuré localement dans le Hospital Node ; aucun service central ne se connecte au DMI.",
          }
        : null,
    notIncluded: NOT_INCLUDED,
    knownLimitations: summary.blockers,
  }
}

/** Lowercase hexadecimal SHA-256 of a UTF-8 text, with Web Crypto. */
export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('')
}

export const PREPARATION_STEPS = [
  'Assemblage du manifeste',
  'Ajout de la configuration du nœud',
  "Calcul de l'empreinte SHA-256",
] as const

export interface PrepareOptions {
  /** Called with the index of the step that starts. */
  onStep?: (index: number) => void
  /** Simulates a failure while adding the configuration (demo scenario). */
  simulateFailure?: boolean
  stepMs?: number
  now?: Date
}

/** Simulated preparation of the package, with its checksum. */
export async function preparePackage(
  snapshot: OnboardingSnapshot,
  { onStep, simulateFailure = false, stepMs = 350, now = new Date() }: PrepareOptions = {},
): Promise<PreparedPackage> {
  const generatedAt = now.toISOString()
  const manifest = buildManifest(snapshot, generatedAt)
  if (!manifest) throw new Error("Le package n'est disponible qu'après l'approbation de l'adhésion.")
  for (const [index] of PREPARATION_STEPS.entries()) {
    onStep?.(index)
    await new Promise((resolve) => setTimeout(resolve, stepMs))
    if (simulateFailure && index === 1) {
      throw new Error('La préparation simulée du package a échoué (scénario de démonstration).')
    }
  }
  const json = `${JSON.stringify(manifest, null, 2)}\n`
  return {
    fileName: `${manifest.node.nodeRef}-package-demo.json`,
    json,
    sha256: await sha256Hex(json),
    sizeBytes: new TextEncoder().encode(json).length,
    generatedAt,
  }
}

/** Returns the snapshot with the download recorded on the approved application. Pure. */
export function applyDownload(snapshot: OnboardingSnapshot, prepared: PreparedPackage, downloadedAt: string): OnboardingSnapshot {
  const application = snapshot.application
  if (application?.status !== 'approved') throw new Error("Le package n'est disponible qu'après l'approbation de l'adhésion.")
  const record: NodePackageRecord = {
    fileName: prepared.fileName,
    sha256: prepared.sha256,
    sizeBytes: prepared.sizeBytes,
    generatedAt: prepared.generatedAt,
    downloadedAt,
  }
  const next = { ...application, nodePackage: record }
  return { ...snapshot, application: next, steps: deriveSteps(snapshot.organization, next) }
}
