import { Alert, Badge, Card, EmptyState, PageHeader } from '@hackcure/design-system'
import { stepStatusDisplay } from '../presentation'
import type { OnboardingStep } from '../types/onboarding'

interface StepPlaceholderViewProps {
  step: OnboardingStep
  position: number
}

/** Frame for a page whose content is delivered by a later ticket (HC-051 to HC-063). */
export function StepPlaceholderView({ step, position }: StepPlaceholderViewProps) {
  const display = stepStatusDisplay[step.status]
  return (
    <>
      <PageHeader
        eyebrow={`Étape ${position} · ${step.ticket}`}
        title={step.label}
        actions={<Badge tone={display.tone}>{display.label}</Badge>}
      />
      {step.status === 'locked' && (
        <Alert tone="neutral" title="Étape verrouillée" className="mb-6">
          {step.detail}
        </Alert>
      )}
      <Card>
        <EmptyState
          title={`Écran prévu par ${step.ticket}`}
          description={`Le shell du portail (HC-050) réserve cette page ; son contenu n'est pas encore implémenté. État actuel du dossier : ${step.detail}`}
        />
      </Card>
    </>
  )
}
