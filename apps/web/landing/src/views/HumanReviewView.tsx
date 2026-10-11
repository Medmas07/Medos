import { useState } from 'react'
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
import { formatDateTime } from '../presentation'
import { REQUIRED_DOCUMENTS } from '../services/documentService'
import {
  applicationNotifications,
  humanReviewState,
  outstandingDocuments,
  refreshReviewState,
  supplementsSinceSubmission,
} from '../services/humanReviewService'
import type { HospitalApplication, OnboardingSnapshot, StepId } from '../types/onboarding'

interface HumanReviewViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make the refresh fail. */
  consumeSimulatedFailure: () => boolean
  onNavigate: (step: StepId) => void
}

const documentLabel = (type: string) => REQUIRED_DOCUMENTS.find((r) => r.type === type)?.label ?? type

export function HumanReviewView({ snapshot, consumeSimulatedFailure, onNavigate }: HumanReviewViewProps) {
  const { application } = snapshot
  const state = humanReviewState(application)

  const header = (
    <PageHeader
      eyebrow="Étape 8 · Parcours d'adhésion"
      title="Validation humaine"
      description="Revue de votre dossier par l'Autorité de gouvernance et d'éthique, après les contrôles automatisés."
      actions={<DemoBadge>Statut simulé</DemoBadge>}
    />
  )

  if (state.kind === 'not_submitted') {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Dossier non transmis"
            description="La revue humaine commence après la transmission du dossier, depuis la revue automatisée."
            action={
              <Button onClick={() => onNavigate(application ? 'automated-review' : 'registration')}>
                {application ? 'Aller à la revue automatisée' : "Aller à l'inscription"}
              </Button>
            }
          />
        </Card>
      </>
    )
  }

  if (state.kind === 'not_recorded') {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune revue humaine enregistrée"
            description="Cette candidature a été instruite avant l'introduction du suivi de la revue humaine."
          />
        </Card>
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="info" title="Une décision humaine, prise par l'Autorité de gouvernance">
          Le portail affiche l'état de la revue ; il ne permet ni de l'accélérer, ni d'y répondre à la place de
          l'Autorité, ni d'approuver la candidature. Les remarques de la revue assistée restent indicatives.
        </Alert>
        {state.kind === 'pending' ? (
          <PendingReview
            application={application!}
            state={state}
            snapshot={snapshot}
            consumeSimulatedFailure={consumeSimulatedFailure}
            onNavigate={onNavigate}
          />
        ) : (
          <Card
            title="Revue humaine terminée"
            actions={<Badge tone="success">Terminée</Badge>}
            footer={
              <div className="flex justify-end">
                <Button onClick={() => onNavigate('decision')}>Voir la décision</Button>
              </div>
            }
          >
            <p className="text-slate-700">
              {state.completedAt ? `Revue terminée le ${formatDateTime(state.completedAt)}. ` : ''}
              {state.decided
                ? "La décision de l'Autorité de gouvernance est disponible."
                : "La décision de l'Autorité de gouvernance sera publiée prochainement."}
            </p>
          </Card>
        )}
      </div>
    </>
  )
}

type Refresh = { kind: 'idle' } | { kind: 'refreshing' } | { kind: 'done'; checkedAt: string } | { kind: 'failed'; message: string }

function PendingReview({
  application,
  state,
  snapshot,
  consumeSimulatedFailure,
  onNavigate,
}: {
  application: HospitalApplication
  state: { reviewerAssigned: boolean; submittedAt: string }
  snapshot: OnboardingSnapshot
  consumeSimulatedFailure: () => boolean
  onNavigate: (step: StepId) => void
}) {
  const [refresh, setRefresh] = useState<Refresh>({ kind: 'idle' })
  const outstanding = outstandingDocuments(application)
  const supplements = supplementsSinceSubmission(application)
  const notifications = applicationNotifications(snapshot)
  const automated = application.reviewSteps.filter((s) => s.step !== 'human_review' && s.completedAt)
  const lastAutomated = automated.map((s) => s.completedAt!).sort().at(-1)

  const timeline: TimelineItem[] = [
    {
      id: 'submitted',
      title: 'Dossier transmis',
      timestamp: formatDateTime(state.submittedAt),
      dateTime: state.submittedAt,
      tone: 'success',
    },
    ...(lastAutomated
      ? [
          {
            id: 'automated',
            title: 'Contrôles automatisés terminés',
            timestamp: formatDateTime(lastAutomated),
            dateTime: lastAutomated,
            description: 'Complétude et revue assistée (simulée, indicative).',
            tone: 'success' as const,
          },
        ]
      : []),
    {
      id: 'human',
      title: "Revue humaine par l'Autorité de gouvernance",
      timestamp: 'En cours',
      description: state.reviewerAssigned ? 'Un réviseur de l’Autorité est désigné.' : 'En attente de désignation d’un réviseur.',
      tone: 'info',
      current: true,
    },
    { id: 'decision', title: 'Décision', timestamp: 'À venir', description: "Publiée par l'Autorité de gouvernance.", tone: 'neutral' },
  ]

  const check = async () => {
    setRefresh({ kind: 'refreshing' })
    try {
      const { checkedAt } = await refreshReviewState(snapshot, { simulateFailure: consumeSimulatedFailure() })
      setRefresh({ kind: 'done', checkedAt })
    } catch (error) {
      setRefresh({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
    }
  }

  return (
    <>
      {outstanding.length > 0 && (
        <Alert
          tone="warning"
          title="Pièces attendues par l'Autorité"
          actions={<Button onClick={() => onNavigate('documents')}>Fournir les documents</Button>}
        >
          {outstanding.map((d) => documentLabel(d.type)).join(', ')} : à fournir pour compléter votre dossier pendant la
          revue.
        </Alert>
      )}
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card
          title="Avancement"
          actions={<Badge tone="info">En revue humaine</Badge>}
          footer={
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-slate-500">
                {refresh.kind === 'done'
                  ? `Statut vérifié le ${formatDateTime(refresh.checkedAt)} : aucune décision pour l'instant.`
                  : 'Aucun délai de décision n’est communiqué.'}
              </span>
              <Button size="sm" variant="secondary" loading={refresh.kind === 'refreshing'} onClick={() => void check()}>
                Actualiser
              </Button>
            </div>
          }
        >
          {refresh.kind === 'failed' && (
            <Alert tone="danger" title="Actualisation impossible" className="mb-4">
              {refresh.message} Le dernier état connu reste affiché.
            </Alert>
          )}
          <Timeline label="Avancement de la revue" items={timeline} />
        </Card>
        <div className="space-y-6">
          <Card title="Compléments depuis la transmission">
            {supplements.length > 0 ? (
              <ul className="space-y-2">
                {supplements.map((d) => (
                  <li key={d.type}>
                    <p className="font-medium text-slate-900">{documentLabel(d.type)}</p>
                    <p className="text-xs text-slate-500">
                      {d.upload!.fileName} · déposé le {formatDateTime(d.upload!.uploadedAt)}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-600">Aucun complément déposé.</p>
            )}
          </Card>
          <Card title="Notifications" actions={<DemoBadge>Simulées</DemoBadge>}>
            {notifications.length > 0 ? (
              <ul className="space-y-3">
                {notifications.map((n) => (
                  <li key={n.id}>
                    <p className="font-medium text-slate-900">{n.title}</p>
                    <p className="text-slate-600">{n.body}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(n.createdAt)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-600">Aucune notification.</p>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
