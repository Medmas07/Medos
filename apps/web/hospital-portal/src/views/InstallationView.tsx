import { useState } from 'react'
import { Alert, Badge, Button, Card, CheckboxField, DemoBadge, EmptyState, PageHeader, type Tone } from '@hackcure/design-system'
import {
  applyChecklist,
  GUIDE_STATUS_LABELS,
  INSTALLATION_STEP_COUNT,
  installationGuide,
  type GuideStep,
  type GuideStepStatus,
} from '../services/installationService'
import type { OnboardingSnapshot, StepId } from '../types/onboarding'

interface InstallationViewProps {
  snapshot: OnboardingSnapshot
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

const statusTone: Record<GuideStepStatus, Tone> = {
  requirement: 'warning',
  demo: 'info',
  planned: 'neutral',
  open: 'neutral',
}

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setState('copied')
    } catch {
      setState('failed')
    }
  }
  return (
    <Button size="sm" variant="ghost" onClick={() => void copy()}>
      {state === 'copied' ? 'Copié' : state === 'failed' ? 'Copie impossible : sélectionnez le texte' : 'Copier'}
    </Button>
  )
}

export function InstallationView({ snapshot, onUpdated, onNavigate }: InstallationViewProps) {
  const guide = installationGuide(snapshot)
  const done = new Set(snapshot.application?.installationChecklist ?? [])

  const header = (
    <PageHeader
      eyebrow="Hospital Node · Étape 12"
      title="Guide d'installation"
      description="Étapes à suivre par votre administrateur pour installer le Hospital Node dans votre établissement."
      actions={<DemoBadge>Installation de démonstration</DemoBadge>}
    />
  )

  if (!guide) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Disponible après approbation"
            description="Le guide s'applique au package préparé après l'approbation de votre adhésion."
            action={
              <Button variant="secondary" onClick={() => onNavigate('decision')}>
                Voir la décision
              </Button>
            }
          />
        </Card>
      </>
    )
  }

  const declared = guide.filter((s) => done.has(s.id)).length

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="info" title="Vous gardez la main">
          Le portail n'installe rien et ne se connecte pas à votre infrastructure. Votre administrateur exécute chaque
          étape lui-même. Les étapes cochées sont votre déclaration ; elles ne sont pas vérifiées par le portail.
        </Alert>
        {!snapshot.application?.nodePackage && (
          <Alert
            tone="warning"
            title="Package non téléchargé"
            actions={<Button onClick={() => onNavigate('node-download')}>Télécharger le package</Button>}
          >
            Plusieurs étapes utilisent le fichier du package et son empreinte.
          </Alert>
        )}
        <Badge tone={declared === INSTALLATION_STEP_COUNT ? 'success' : 'neutral'}>
          {`${declared} / ${INSTALLATION_STEP_COUNT} étapes déclarées`}
        </Badge>

        <ol className="space-y-4">
          {guide.map((step, index) => (
            <li key={step.id}>
              <GuideCard
                step={step}
                index={index + 1}
                done={done.has(step.id)}
                onToggle={(value) => onUpdated(applyChecklist(snapshot, step.id, value))}
              />
            </li>
          ))}
        </ol>

        {declared === INSTALLATION_STEP_COUNT && (
          <Alert
            tone="success"
            title="Installation déclarée terminée"
            actions={<Button onClick={() => onNavigate('node-status')}>Voir l'état du nœud</Button>}
          >
            Cette déclaration n'est pas une vérification : l'état réel du nœud se consulte sur la page État du nœud.
          </Alert>
        )}
      </div>
    </>
  )
}

function GuideCard({
  step,
  index,
  done,
  onToggle,
}: {
  step: GuideStep
  index: number
  done: boolean
  onToggle: (done: boolean) => void
}) {
  const actionable = step.status !== 'planned'
  return (
    <Card
      title={`${index}. ${step.title}`}
      actions={<Badge tone={statusTone[step.status]}>{GUIDE_STATUS_LABELS[step.status]}</Badge>}
      footer={
        actionable ? (
          <CheckboxField label="Étape effectuée" checked={done} onChange={(e) => onToggle(e.target.checked)} />
        ) : (
          <CheckboxField
            label="Rien à exécuter aujourd'hui : cocher pour confirmer la lecture"
            checked={done}
            onChange={(e) => onToggle(e.target.checked)}
          />
        )
      }
    >
      <p className="text-slate-700">{step.body}</p>
      {step.warning && (
        <Alert tone="warning" title="Limite connue" className="mt-3">
          {step.warning}
        </Alert>
      )}
      {step.commands && (
        <div className="mt-3">
          <div className="flex justify-end">
            <CopyButton text={step.commands} />
          </div>
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
            <code>{step.commands}</code>
          </pre>
        </div>
      )}
    </Card>
  )
}
