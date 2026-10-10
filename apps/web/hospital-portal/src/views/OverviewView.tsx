import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  Timeline,
  type TimelineItem,
} from '@hackcure/design-system'
import { applicationStatusDisplay, formatDateTime, stepStatusDisplay } from '../presentation'
import type { OnboardingSnapshot, StepId } from '../types/onboarding'

interface OverviewViewProps {
  snapshot: OnboardingSnapshot
  onNavigate: (step: StepId) => void
}

export function OverviewView({ snapshot, onNavigate }: OverviewViewProps) {
  const { organization, application, steps, notifications } = snapshot
  const completed = steps.filter((s) => s.status === 'completed').length
  const nextStep = steps.find((s) => s.status !== 'completed' && s.status !== 'locked')

  const timelineItems: TimelineItem[] = steps.map((step) => {
    const display = stepStatusDisplay[step.status]
    return {
      id: step.id,
      title: (
        <a
          href={`#${step.id}`}
          onClick={(e) => {
            e.preventDefault()
            onNavigate(step.id)
          }}
          className="hover:underline"
        >
          {step.label}
        </a>
      ),
      timestamp: step.ticket,
      description: step.detail,
      meta: <Badge tone={display.tone}>{display.label}</Badge>,
      tone: display.tone,
      current: step.id === nextStep?.id,
    }
  })

  return (
    <>
      <PageHeader
        eyebrow="Adhésion à l'écosystème fédéré"
        title="Tableau de bord d'adhésion"
        description={`Suivi de la candidature de ${organization.name} (${organization.city}), de l'inscription au téléchargement du Hospital Node.`}
      />

      <Alert tone="info" title="Ce portail soumet, l'Autorité de gouvernance décide" className="mb-6">
        Le Portail Hospitalier transmet votre dossier et affiche les décisions. L'approbation relève
        exclusivement de l'Autorité de gouvernance et d'éthique ; ni ce portail ni l'opérateur de la
        plateforme ne peuvent approuver une candidature.
      </Alert>

      {!application ? (
        <Card className="mb-6">
          <EmptyState
            title="Aucune candidature soumise"
            description="Commencez par l'inscription de votre établissement pour lancer le parcours d'adhésion."
            action={<Button onClick={() => onNavigate('registration')}>Commencer l'inscription</Button>}
          />
        </Card>
      ) : (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <Card title="Statut de la candidature" actions={<DemoBadge>Fictif</DemoBadge>}>
            <Badge tone={applicationStatusDisplay[application.status].tone}>
              {applicationStatusDisplay[application.status].label}
            </Badge>
            <p className="mt-2 text-xs text-slate-500">
              {application.id} · {application.status === 'draft' ? 'enregistrée' : 'soumise'} le{' '}
              {formatDateTime(application.submittedAt)}
            </p>
          </Card>
          <Card title="Progression">
            <p className="text-2xl font-semibold text-slate-900">
              {completed} / {steps.length}
            </p>
            <p className="text-xs text-slate-500">étapes terminées</p>
          </Card>
          <Card title="Prochaine étape">
            {nextStep ? (
              <>
                <p className="font-medium text-slate-900">{nextStep.label}</p>
                <p className="text-xs text-slate-500">{nextStep.detail}</p>
              </>
            ) : (
              <p className="text-slate-600">Aucune action en attente.</p>
            )}
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card title="Parcours d'adhésion" description="États dérivés des données fictives HC-005.">
          <Timeline label="Étapes d'adhésion" items={timelineItems} />
        </Card>
        <Card title="Notifications" actions={<DemoBadge>Simulées</DemoBadge>}>
          {notifications.length === 0 ? (
            <EmptyState title="Aucune notification" />
          ) : (
            <ul className="space-y-3">
              {notifications.map((n) => (
                <li key={n.id}>
                  <p className="font-medium text-slate-900">{n.title}</p>
                  <p className="text-slate-600">{n.body}</p>
                  <p className="text-xs text-slate-500">{formatDateTime(n.createdAt)}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
