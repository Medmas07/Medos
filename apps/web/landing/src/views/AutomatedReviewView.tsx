import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CheckboxField,
  DemoBadge,
  EmptyState,
  LoadingState,
  PageHeader,
} from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import {
  ASSISTED_REVIEW_PROVENANCE,
  canSubmit,
  runAutomatedReview,
  submitForReview,
  type Finding,
  type ReviewResult,
} from '../services/reviewService'
import type { OnboardingSnapshot, ReviewStep, StepId } from '../types/onboarding'

interface AutomatedReviewViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make the submission fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

export function AutomatedReviewView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: AutomatedReviewViewProps) {
  const { application } = snapshot
  const [justSubmitted, setJustSubmitted] = useState(false)

  const header = (
    <PageHeader
      eyebrow="Étape 7 · Parcours d'adhésion"
      title="Revue automatisée"
      description="Contrôle de complétude, puis revue assistée indicative, avant la revue humaine de l'Autorité de gouvernance."
      actions={<DemoBadge>Contrôles simulés</DemoBadge>}
    />
  )

  const pipeline = (
    <ol aria-label="Étapes de la revue" className="flex flex-wrap items-center gap-2 text-sm">
      <li><Badge tone="info">1. Complétude (bloquante)</Badge></li>
      <li aria-hidden="true" className="text-slate-400">→</li>
      <li><Badge tone="demo">2. Revue assistée (simulée, indicative)</Badge></li>
      <li aria-hidden="true" className="text-slate-400">→</li>
      <li><Badge tone="neutral">3. Revue humaine (Autorité de gouvernance)</Badge></li>
    </ol>
  )

  if (!application) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune inscription"
            description="Inscrivez d'abord votre établissement ; la revue porte sur le dossier complet."
            action={<Button onClick={() => onNavigate('registration')}>Aller à l'inscription</Button>}
          />
        </Card>
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        {pipeline}
        <Alert tone="info" title="Aucune approbation automatique">
          Ces contrôles préparent la revue humaine. Seule l'Autorité de gouvernance et d'éthique décide de l'adhésion ;
          la revue assistée n'est qu'une aide indicative.
        </Alert>
        {justSubmitted && (
          <Alert
            tone="success"
            title="Dossier transmis pour revue humaine (simulation)"
            actions={<Button onClick={() => onNavigate('human-review')}>Voir la validation humaine</Button>}
          >
            Votre dossier est désormais verrouillé. Il est conservé dans cette page jusqu'à son rechargement.
          </Alert>
        )}
        {application.status === 'draft' ? (
          <DraftReview
            snapshot={snapshot}
            consumeSimulatedFailure={consumeSimulatedFailure}
            onNavigate={onNavigate}
            onSubmitted={(next) => {
              onUpdated(next)
              setJustSubmitted(true)
            }}
          />
        ) : (
          <RecordedReview steps={application.reviewSteps} onNavigate={onNavigate} />
        )}
      </div>
    </>
  )
}

function FindingList({
  findings,
  actionLabel,
  onNavigate,
}: {
  findings: Finding[]
  /** "Corriger" for blocking findings, "Voir" for advisory remarks. */
  actionLabel: string
  onNavigate: (step: StepId) => void
}) {
  return (
    <ul className="space-y-2">
      {findings.map((finding) => (
        <li key={finding.message} className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-slate-800">{finding.message}</span>
          {finding.step && (
            <Button size="sm" variant="ghost" onClick={() => onNavigate(finding.step!)}>
              {actionLabel}
            </Button>
          )}
        </li>
      ))}
    </ul>
  )
}

function CompletenessCard({ findings, at, onNavigate }: { findings: Finding[]; at: string | null; onNavigate: (step: StepId) => void }) {
  return (
    <Card
      title="Contrôle de complétude"
      description={at ? `Effectué le ${formatDateTime(at)}.` : undefined}
      actions={
        <Badge tone={findings.length > 0 ? 'warning' : 'success'}>
          {findings.length > 0 ? `${findings.length} point(s) à corriger` : 'Dossier complet'}
        </Badge>
      }
    >
      {findings.length > 0 ? (
        <FindingList findings={findings} actionLabel="Corriger" onNavigate={onNavigate} />
      ) : (
        <p className="text-slate-700">Toutes les étapes requises sont renseignées.</p>
      )}
    </Card>
  )
}

function AssistedCard({ findings, at, onNavigate }: { findings: Finding[]; at: string | null; onNavigate: (step: StepId) => void }) {
  return (
    <Card
      title="Revue assistée"
      description={at ? `Effectuée le ${formatDateTime(at)}.` : undefined}
      actions={<DemoBadge>IA simulée · indicatif</DemoBadge>}
    >
      <p className="mb-3 text-xs text-slate-500">{ASSISTED_REVIEW_PROVENANCE}</p>
      {findings.length > 0 ? (
        <FindingList findings={findings} actionLabel="Voir" onNavigate={onNavigate} />
      ) : (
        <p className="text-slate-700">Aucune incohérence relevée.</p>
      )}
    </Card>
  )
}

type Run = { kind: 'idle' } | { kind: 'running' } | { kind: 'done'; result: ReviewResult }
type Submit = { kind: 'idle' } | { kind: 'submitting' } | { kind: 'failed'; message: string }

function DraftReview({
  snapshot,
  consumeSimulatedFailure,
  onNavigate,
  onSubmitted,
}: {
  snapshot: OnboardingSnapshot
  consumeSimulatedFailure: () => boolean
  onNavigate: (step: StepId) => void
  onSubmitted: (snapshot: OnboardingSnapshot) => void
}) {
  const [run, setRun] = useState<Run>({ kind: 'idle' })
  const [confirmed, setConfirmed] = useState(false)
  const [submit, setSubmit] = useState<Submit>({ kind: 'idle' })
  const result = run.kind === 'done' ? run.result : null
  const submitting = submit.kind === 'submitting'

  const start = async () => {
    setRun({ kind: 'running' })
    setRun({ kind: 'done', result: await runAutomatedReview(snapshot) })
  }

  const send = async () => {
    setSubmit({ kind: 'submitting' })
    try {
      onSubmitted(await submitForReview(snapshot, confirmed, { simulateFailure: consumeSimulatedFailure() }))
    } catch (error) {
      setSubmit({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
    }
  }

  if (run.kind === 'running') {
    return (
      <Card>
        <LoadingState label="Contrôle de complétude, puis revue assistée simulée…" />
      </Card>
    )
  }

  if (!result) {
    return (
      <Card>
        <EmptyState
          title="Contrôles non lancés"
          description="Lancez les contrôles pour vérifier votre dossier avant de le transmettre. Vous pouvez les relancer après chaque correction."
          action={<Button onClick={() => void start()}>Lancer les contrôles</Button>}
        />
      </Card>
    )
  }

  return (
    <>
      <CompletenessCard findings={result.completeness} at={result.ranAt} onNavigate={onNavigate} />
      <AssistedCard findings={result.assisted} at={result.ranAt} onNavigate={onNavigate} />
      <div className="flex justify-end">
        <Button variant="secondary" disabled={submitting} onClick={() => void start()}>
          Relancer les contrôles
        </Button>
      </div>
      {canSubmit(snapshot.application, result) ? (
        <Card
          title="Transmettre pour revue humaine"
          footer={
            <div className="flex justify-end">
              <Button disabled={!confirmed} loading={submitting} onClick={() => void send()}>
                {submit.kind === 'failed' ? 'Réessayer' : 'Transmettre le dossier'}
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            {submit.kind === 'failed' && (
              <Alert tone="danger" title="Dossier non transmis">
                {submit.message}
              </Alert>
            )}
            <CheckboxField
              label="Je confirme la transmission du dossier à l'Autorité de gouvernance. Après transmission, il ne pourra plus être modifié depuis le portail."
              hint="La transmission ne vaut pas approbation."
              checked={confirmed}
              disabled={submitting}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
          </div>
        </Card>
      ) : (
        <Alert tone="warning" title="Transmission impossible pour l'instant">
          Corrigez les points du contrôle de complétude, puis relancez les contrôles. Les remarques de la revue assistée
          ne bloquent pas la transmission.
        </Alert>
      )}
    </>
  )
}

function RecordedReview({ steps, onNavigate }: { steps: ReviewStep[]; onNavigate: (step: StepId) => void }) {
  const completeness = steps.find((s) => s.step === 'completeness_check')
  const assisted = steps.find((s) => s.step === 'assisted_review')
  if (!completeness) {
    return (
      <Card>
        <EmptyState title="Aucun résultat enregistré" description="Cette candidature a été instruite sans revue automatisée." />
      </Card>
    )
  }
  const asFindings = (step?: ReviewStep): Finding[] => (step?.findings ?? []).map((message) => ({ message }))
  return (
    <>
      <Alert tone="neutral" title="Résultats enregistrés lors de la transmission">
        Ils reflètent le dossier au moment des contrôles. Les compléments apportés depuis sont examinés lors de la revue
        humaine.
      </Alert>
      <CompletenessCard findings={asFindings(completeness)} at={completeness.completedAt} onNavigate={onNavigate} />
      {assisted && <AssistedCard findings={asFindings(assisted)} at={assisted.completedAt} onNavigate={onNavigate} />}
      <div className="flex justify-end">
        <Button variant="secondary" onClick={() => onNavigate('human-review')}>
          Voir la validation humaine
        </Button>
      </div>
    </>
  )
}
