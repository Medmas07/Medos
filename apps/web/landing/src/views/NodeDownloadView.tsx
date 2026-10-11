import { useState } from 'react'
import { Alert, Badge, Button, Card, DemoBadge, EmptyState, PageHeader, type Tone } from '@hackcure/design-system'
import { formatSize } from '../services/documentService'
import { nodeConfiguration } from '../services/nodeConfigService'
import {
  applyDownload,
  NOT_INCLUDED,
  PREPARATION_STEPS,
  preparePackage,
  type PackageItem,
  type PreparedPackage,
} from '../services/nodePackageService'
import { formatDateTime } from '../presentation'
import type { OnboardingSnapshot, StepId } from '../types/onboarding'

interface NodeDownloadViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make the preparation fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

const ITEM_STATUS: Record<PackageItem['status'], { label: string; tone: Tone }> = {
  open: { label: 'Non décidé', tone: 'warning' },
  planned: { label: 'Prévu', tone: 'neutral' },
  installation_package: { label: "Dans le package d'installation", tone: 'info' },
}

const INCLUDED = [
  'Manifeste du package (format de démonstration)',
  'Fichier de configuration du Hospital Node (HC-060)',
  "Références du nœud, de l'établissement et de la décision d'approbation",
  "Environnement déclaré et informations pour l'adaptateur DMI local",
  'Limites connues de cette configuration',
]

/** Saves a text file through the browser; nothing is sent to a server. */
function saveFile(fileName: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

type Preparation =
  | { kind: 'idle' }
  | { kind: 'preparing'; step: number }
  | { kind: 'ready'; prepared: PreparedPackage }
  | { kind: 'failed'; message: string }

export function NodeDownloadView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: NodeDownloadViewProps) {
  const availability = nodeConfiguration(snapshot)
  const [preparation, setPreparation] = useState<Preparation>({ kind: 'idle' })
  const record = snapshot.application?.nodePackage

  const header = (
    <PageHeader
      eyebrow="Hospital Node · Étape 11"
      title="Téléchargement du nœud"
      description="Package de votre Hospital Node, à installer dans votre établissement par votre administrateur."
      actions={<DemoBadge>Package de démonstration</DemoBadge>}
    />
  )

  if (availability.kind !== 'ready') {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title={availability.kind === 'rejected' ? 'Aucun package' : 'Disponible après approbation'}
            description={
              availability.kind === 'rejected'
                ? "La candidature n'a pas été approuvée : aucun Hospital Node n'est distribué."
                : "Le package est préparé après l'approbation de votre adhésion par l'Autorité de gouvernance."
            }
            action={
              <Button variant="secondary" onClick={() => onNavigate(availability.kind === 'no_application' ? 'registration' : 'decision')}>
                {availability.kind === 'no_application' ? "Aller à l'inscription" : 'Voir la décision'}
              </Button>
            }
          />
        </Card>
      </>
    )
  }

  const prepare = async () => {
    setPreparation({ kind: 'preparing', step: 0 })
    try {
      const prepared = await preparePackage(snapshot, {
        simulateFailure: consumeSimulatedFailure(),
        onStep: (step) => setPreparation({ kind: 'preparing', step }),
      })
      setPreparation({ kind: 'ready', prepared })
    } catch (error) {
      setPreparation({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
    }
  }

  const download = (prepared: PreparedPackage) => {
    saveFile(prepared.fileName, prepared.json)
    onUpdated(applyDownload(snapshot, prepared, new Date().toISOString()))
  }

  const { blockers } = availability.summary

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="info" title="Rien n'est installé par ce portail">
          Le package est un fichier de description, sans exécutable ni secret. L'installation se fait chez vous, par
          votre administrateur, avec son accord explicite ; les secrets du nœud sont générés localement à ce moment-là.
        </Alert>
        {blockers.length > 0 && (
          <Alert tone="warning" title="Package de démonstration non exécutable en l'état">
            <ul className="list-disc space-y-1 pl-5">
              {blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          </Alert>
        )}
        {record && (
          <Alert
            tone="success"
            title="Package téléchargé"
            actions={<Button onClick={() => onNavigate('node-installation')}>Continuer : guide d'installation</Button>}
          >
            {record.fileName} · {formatSize(record.sizeBytes)} · téléchargé le {formatDateTime(record.downloadedAt)}. Empreinte
            SHA-256 : <code className="break-all">{record.sha256}</code>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Contenu du package">
            <ul className="list-disc space-y-1.5 pl-5 text-slate-700">
              {INCLUDED.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Card>
          <Card title="Non inclus à ce stade">
            <ul className="space-y-3">
              {NOT_INCLUDED.map((item) => (
                <li key={item.item} className="flex flex-col items-start gap-1">
                  <Badge tone={ITEM_STATUS[item.status].tone}>{ITEM_STATUS[item.status].label}</Badge>
                  <span className="text-slate-700">{item.note}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <Card title="Préparer et télécharger" description="Le package est assemblé dans votre navigateur ; aucun fichier n'est envoyé.">
          {preparation.kind === 'idle' && (
            <Button onClick={() => void prepare()}>{record ? 'Préparer à nouveau' : 'Préparer le package'}</Button>
          )}
          {preparation.kind === 'preparing' && (
            <ol aria-label="Préparation du package" className="space-y-1.5">
              {PREPARATION_STEPS.map((label, index) => (
                <li key={label} className="flex items-center gap-2 text-sm">
                  <Badge tone={index < preparation.step ? 'success' : index === preparation.step ? 'info' : 'neutral'}>
                    {index < preparation.step ? 'Fait' : index === preparation.step ? 'En cours' : 'À venir'}
                  </Badge>
                  <span className="text-slate-700">{label}</span>
                </li>
              ))}
            </ol>
          )}
          {preparation.kind === 'failed' && (
            <Alert tone="danger" title="Package non préparé" actions={<Button variant="secondary" onClick={() => void prepare()}>Réessayer</Button>}>
              {preparation.message}
            </Alert>
          )}
          {preparation.kind === 'ready' && (
            <div className="space-y-4">
              <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-[10rem_1fr]">
                <dt className="text-slate-500">Fichier</dt>
                <dd className="font-medium break-all text-slate-900">{preparation.prepared.fileName}</dd>
                <dt className="text-slate-500">Taille</dt>
                <dd className="font-medium text-slate-900">{formatSize(preparation.prepared.sizeBytes)}</dd>
                <dt className="text-slate-500">SHA-256</dt>
                <dd className="font-mono text-xs break-all text-slate-900">{preparation.prepared.sha256}</dd>
              </dl>
              <Button onClick={() => download(preparation.prepared)}>Télécharger le package</Button>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
