import type { OnboardingSnapshot } from '../types/onboarding'
import { HOSTING_LABELS } from './technicalService'
import { nodeConfiguration } from './nodeConfigService'
import { deriveSteps, INSTALLATION_STEP_COUNT } from './onboardingService'

/**
 * Hospital Node installation guide (HC-062), following the product vision's
 * installation flow. Each step says honestly whether it can be done today with
 * the demo Hospital Node from the repository (`demo`), is a requirement
 * (`requirement`), or is not built yet (`planned`) or not decided (`open`).
 * Commands use the real interfaces: the Hospital Node runtime and its
 * `GET /health`, and the Federation node registry (`node-registry.v1.yaml`).
 * Steps marked done are the hospital's own declaration; nothing here verifies them.
 */

export type GuideStepStatus = 'requirement' | 'demo' | 'planned' | 'open'

export interface GuideStep {
  id: string
  title: string
  status: GuideStepStatus
  body: string
  commands?: string
  warning?: string
}

export const GUIDE_STATUS_LABELS: Record<GuideStepStatus, string> = {
  requirement: 'Obligatoire',
  demo: 'Disponible (démo)',
  planned: 'Prévu',
  open: 'Non décidé',
}

/** Federation Service port (services/federation README) and contract version. */
export const FEDERATION_URL = 'http://localhost:8300'

/** Body of the Federation registry `registerNode` request (`RegistrationRequest`). Pure. */
export function registrationRequest(snapshot: OnboardingSnapshot) {
  const availability = nodeConfiguration(snapshot)
  if (availability.kind !== 'ready') return null
  const { summary } = availability
  return {
    organization_ref: summary.file.organization_ref,
    base_url: summary.federationBaseUrl ?? 'http://localhost:<port>',
    contract_versions: [summary.federationContractVersion],
    approval_decision_ref: summary.approvalDecisionRef,
  }
}

/** The guide for an approved application, or `null` before approval. Pure. */
export function installationGuide(snapshot: OnboardingSnapshot): GuideStep[] | null {
  const availability = nodeConfiguration(snapshot)
  const registration = registrationRequest(snapshot)
  if (availability.kind !== 'ready' || !registration) return null
  const { file, environment: env, blockers } = availability.summary
  const pkg = snapshot.application?.nodePackage
  const packageFile = pkg?.fileName ?? `${file.node_ref}-package-demo.json`
  const configFile = `config/${file.node_ref.replace(/^node-/, '')}.json`
  const port = file.port ?? '<port>'
  const missingRecords = blockers.find((b) => b.includes('dossiers fictifs'))

  return [
    {
      id: 'admin-approval',
      title: "Obtenir l'accord de l'administrateur",
      status: 'requirement',
      body: "Rien ne s'installe sans l'accord explicite de l'administrateur système de l'établissement, qui exécute lui-même chaque étape. Aucun logiciel privilégié n'est installé à son insu.",
    },
    {
      id: 'environment',
      title: "Vérifier l'environnement d'accueil",
      status: 'demo',
      body: env
        ? `Environnement déclaré : ${HOSTING_LABELS[env.hostingType]}, ${env.operatingSystem}, ${env.cpuCores} cœurs, ${env.memoryGb} Go de mémoire. Pour la démonstration, Python 3 suffit.`
        : 'Aucun environnement déclaré dans le questionnaire technique.',
      commands: 'python3 --version',
    },
    {
      id: 'verify-package',
      title: "Vérifier l'intégrité du package",
      status: 'demo',
      body: pkg
        ? `Comparez l'empreinte calculée à celle affichée lors du téléchargement : ${pkg.sha256}.`
        : "Téléchargez d'abord le package depuis la page Téléchargement : son empreinte SHA-256 y est affichée.",
      commands: `sha256sum ${packageFile}`,
    },
    {
      id: 'container-runtime',
      title: 'Détecter un environnement de conteneurs',
      status: 'open',
      body: `${env?.containerRuntimeAvailable ? 'Votre hôte déclare pouvoir exécuter des conteneurs.' : "Votre hôte ne déclare pas d'environnement de conteneurs : un assistant d'installation est prévu pour ce cas."} Le choix des conteneurs n'est pas encore décidé ; la démonstration lance le nœud directement avec Python.`,
    },
    {
      id: 'configuration',
      title: 'Préparer la configuration du nœud',
      status: 'demo',
      body: 'Depuis la racine du dépôt, extrayez la configuration du package vers le dossier lu par le Hospital Node.',
      commands: `python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1]))['hospitalNodeConfig'], indent=2, ensure_ascii=False))" ${packageFile} > instances/hospital-node/${configFile}`,
      warning: missingRecords,
    },
    {
      id: 'local-secrets',
      title: 'Générer les secrets locaux du nœud',
      status: 'planned',
      body: "L'identité et les secrets du nœud seront générés sur place, jamais transmis par le portail. Cette étape n'est pas encore implémentée : il n'y a rien à exécuter aujourd'hui.",
    },
    {
      id: 'launch',
      title: 'Lancer le nœud',
      status: 'demo',
      body: 'Depuis le dossier du Hospital Node, en mode démonstration (écoute sur 127.0.0.1).',
      commands: [
        'cd instances/hospital-node',
        'python3 -m venv .venv && . .venv/bin/activate',
        'pip install -r requirements.txt',
        `HOSPITAL_NODE_CONFIG=${configFile} python main.py`,
      ].join('\n'),
      warning: missingRecords,
    },
    {
      id: 'health-check',
      title: "Vérifier l'état du nœud",
      status: 'demo',
      body: `La réponse doit indiquer "status": "ok" et "node_ref": "${file.node_ref}". Ce contrôle de vivacité ne vérifie ni le DMI ni la fédération.`,
      commands: `curl http://127.0.0.1:${port}/health`,
    },
    {
      id: 'registration',
      title: 'Inscrire le nœud au registre de fédération',
      status: 'demo',
      body: "L'inscription cite la décision d'approbation. En démonstration, l'écriture du registre n'est pas authentifiée et la référence d'approbation n'est pas vérifiée auprès du Governance Node.",
      commands: [
        `curl -X PUT ${FEDERATION_URL}/v1/registry/nodes/${file.node_ref} \\`,
        "  -H 'Content-Type: application/json' \\",
        `  -d '${JSON.stringify(registration)}'`,
      ].join('\n'),
    },
  ]
}

/** Returns the snapshot with a guide step declared done or not done (approved applications only). Pure. */
export function applyChecklist(snapshot: OnboardingSnapshot, stepId: string, done: boolean): OnboardingSnapshot {
  const guide = installationGuide(snapshot)
  const application = snapshot.application
  if (!guide || !application) throw new Error("Le guide d'installation n'est disponible qu'après l'approbation.")
  if (!guide.some((s) => s.id === stepId)) throw new Error(`Étape inconnue : ${stepId}`)
  const current = new Set(application.installationChecklist ?? [])
  if (done) current.add(stepId)
  else current.delete(stepId)
  const installationChecklist = guide.map((s) => s.id).filter((id) => current.has(id))
  const next = { ...application, installationChecklist }
  return { ...snapshot, application: next, steps: deriveSteps(snapshot.organization, next) }
}

export { INSTALLATION_STEP_COUNT }
