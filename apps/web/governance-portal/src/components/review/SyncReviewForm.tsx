import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  CheckboxField,
  DemoBadge,
  TextareaField,
  TextField,
  type Tone,
} from '@hackcure/design-system'
import { MIN_RATIONALE_LENGTH } from '../../services/hospitalReview'
import { reviewStore } from '../../services/reviewStore'
import {
  InvalidSyncReview,
  initialSyncDraft,
  maxApprovedDays,
  recordSyncReview,
  syncChecks,
  validateSyncReview,
  type SyncCheckState,
  type SyncReviewContext,
  type SyncReviewDraft,
  type SyncReviewField,
  type SyncReviewIssue,
} from '../../services/syncReview'
import type { PersonInfo } from '../../types/governance'

/** Simulated round trip to the Governance Node; the real API (HC-132) is PLANNED. */
const SIMULATED_DELAY_MS = 900
const DAY_MS = 24 * 60 * 60 * 1000

const CHECK_BADGES: Record<SyncCheckState, { tone: Tone; label: string }> = {
  pass: { tone: 'success', label: 'Conforme' },
  fail: { tone: 'danger', label: 'Non conforme' },
  manual: { tone: 'warning', label: 'À vérifier' },
}

type Step = 'editing' | 'confirming' | 'submitting'

interface SyncReviewFormProps {
  /** Everything but the time: the form reads the clock itself. */
  context: Omit<SyncReviewContext, 'now'>
  reviewer: PersonInfo | undefined
  reviewerName: string
}

function issueFor(issues: SyncReviewIssue[], field: SyncReviewField): string | undefined {
  return issues.find((i) => i.field === field)?.message
}

const formatDate = (date: Date) => date.toLocaleDateString('fr-TN')

export function SyncReviewForm({ context: request, reviewer, reviewerName }: SyncReviewFormProps) {
  // Checks and the default duration use the time the form opened; the decision is
  // dated when it is confirmed.
  const [openedAt] = useState(() => new Date())
  const context: SyncReviewContext = { ...request, now: openedAt }
  const [draft, setDraft] = useState<SyncReviewDraft>(() => initialSyncDraft(context))
  const [conditionsText, setConditionsText] = useState('')
  const [step, setStep] = useState<Step>('editing')
  const [showIssues, setShowIssues] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => () => clearTimeout(timer.current), [])

  const checks = syncChecks(context)
  const approvalBlocked = checks.some((c) => c.state === 'fail')
  const needsManual = checks.some((c) => c.state === 'manual')
  const maxDays = maxApprovedDays(context)
  const currentDraft: SyncReviewDraft = { ...draft, conditions: conditionsText.split('\n') }
  const issues = validateSyncReview(context, currentDraft, reviewer)
  const visibleIssues = showIssues ? issues : []
  const blocking = issues.filter((i) => i.field === 'request' || i.field === 'reviewer')
  const endsOn = new Date(context.now.getTime() + draft.approvedDays * DAY_MS)

  const update = (changes: Partial<SyncReviewDraft>) => setDraft((d) => ({ ...d, ...changes }))

  const review = () => {
    setShowIssues(true)
    if (issues.length === 0) setStep('confirming')
  }

  const confirm = () => {
    setStep('submitting')
    timer.current = setTimeout(() => {
      try {
        reviewStore.recordSync(
          recordSyncReview(
            { ...context, now: new Date() },
            currentDraft,
            reviewer,
            reviewStore.nextSequence(),
          ),
        )
      } catch (error) {
        if (!(error instanceof InvalidSyncReview)) throw error
        setShowIssues(true)
        setStep('editing')
      }
    }, SIMULATED_DELAY_MS)
  }

  if (blocking.length > 0) {
    return (
      <Alert tone="danger" title="Décision impossible">
        {blocking.map((i) => i.message).join(' ')}
      </Alert>
    )
  }

  const approving = draft.outcome === 'approved'

  if (step !== 'editing') {
    const conditions = currentDraft.conditions.map((c) => c.trim()).filter(Boolean)
    return (
      <div className="space-y-3 text-xs">
        <Alert
          tone={approving ? 'success' : 'danger'}
          title={approving ? `Autoriser ${context.request.id}` : `Refuser ${context.request.id}`}
        >
          <p>« {draft.rationale.trim()} »</p>
          {approving && (
            <p className="mt-1">
              Autorisation temporaire de {draft.approvedDays} jours, jusqu’au {formatDate(endsOn)}.
            </p>
          )}
          {approving && conditions.length > 0 && (
            <ul className="mt-1 list-disc space-y-0.5 pl-4">
              {conditions.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          )}
          <p className="mt-2">
            Décision de {reviewerName}. Elle sera enregistrée dans l’état local du portail avec un
            événement d’audit, sans être transmise au Nœud de Gouvernance ni aux nœuds hospitaliers.
          </p>
        </Alert>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={approving ? 'primary' : 'danger'}
            loading={step === 'submitting'}
            disabled={step === 'submitting'}
            onClick={confirm}
          >
            {step === 'submitting' ? 'Enregistrement simulé…' : 'Confirmer la décision'}
          </Button>
          <Button variant="ghost" disabled={step === 'submitting'} onClick={() => setStep('editing')}>
            Modifier
          </Button>
          <DemoBadge>Simulé — non persisté</DemoBadge>
        </div>
      </div>
    )
  }

  return (
    <form
      className="space-y-4 text-xs"
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        review()
      }}
    >
      <div className="flex items-center justify-between">
        <h4 className="font-semibold uppercase tracking-wider text-slate-600">Décision de l’Autorité</h4>
        <DemoBadge>Simulé — HC-132 planifié</DemoBadge>
      </div>

      <ul className="space-y-2" aria-label="Contrôles préalables">
        {checks.map((check) => (
          <li key={check.id} className="rounded-md border border-slate-200 bg-slate-50 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-slate-800">{check.label}</span>
              <Badge tone={CHECK_BADGES[check.state].tone} dot>
                {CHECK_BADGES[check.state].label}
              </Badge>
            </div>
            <p className="mt-1 text-slate-600">{check.detail}</p>
          </li>
        ))}
      </ul>

      {approvalBlocked && (
        <Alert tone="warning" title="Autorisation impossible">
          Un contrôle n’est pas conforme : seul un refus motivé peut être enregistré.
        </Alert>
      )}

      <fieldset className="space-y-1.5">
        <legend className="font-medium text-slate-800">
          Décision<span aria-hidden="true" className="ml-0.5 text-danger-700">*</span>
        </legend>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={approving ? 'primary' : 'secondary'}
            aria-pressed={approving}
            disabled={approvalBlocked}
            onClick={() => update({ outcome: 'approved' })}
          >
            Autoriser
          </Button>
          <Button
            type="button"
            size="sm"
            variant={draft.outcome === 'rejected' ? 'danger' : 'secondary'}
            aria-pressed={draft.outcome === 'rejected'}
            onClick={() => update({ outcome: 'rejected' })}
          >
            Refuser
          </Button>
        </div>
        {issueFor(visibleIssues, 'outcome') && (
          <p className="font-medium text-danger-700">{issueFor(visibleIssues, 'outcome')}</p>
        )}
        {issueFor(visibleIssues, 'checks') && (
          <p className="font-medium text-danger-700">{issueFor(visibleIssues, 'checks')}</p>
        )}
      </fieldset>

      {approving && (
        <>
          <TextField
            label="Durée autorisée (jours)"
            type="number"
            min={1}
            max={maxDays}
            step={1}
            required
            value={Number.isNaN(draft.approvedDays) ? '' : draft.approvedDays}
            onChange={(e) => update({ approvedDays: e.target.valueAsNumber })}
            hint={`Entre 1 et ${maxDays} jours. Fin de l’autorisation : ${
              Number.isInteger(draft.approvedDays) && draft.approvedDays >= 1 ? formatDate(endsOn) : '—'
            }.`}
            error={issueFor(visibleIssues, 'duration')}
          />
          {needsManual && (
            <CheckboxField
              label="J’ai vérifié la base d’autorisation hors du portail."
              hint="Le portail ne peut pas vérifier ce document lui-même."
              checked={draft.manualChecksConfirmed}
              onChange={(e) => update({ manualChecksConfirmed: e.target.checked })}
              error={issueFor(visibleIssues, 'manual')}
            />
          )}
          <TextareaField
            label="Conditions"
            rows={2}
            value={conditionsText}
            onChange={(e) => setConditionsText(e.target.value)}
            placeholder="Aucune réutilisation à des fins de recherche."
            hint="Facultatif. Une condition par ligne."
          />
        </>
      )}

      <TextareaField
        label="Motivation"
        required
        rows={3}
        value={draft.rationale}
        onChange={(e) => update({ rationale: e.target.value })}
        hint={`Au moins ${MIN_RATIONALE_LENGTH} caractères. Elle figurera dans la décision.`}
        error={issueFor(visibleIssues, 'rationale')}
      />

      <div className="flex items-center gap-2">
        <Button type="submit">Vérifier la décision</Button>
        {showIssues && issues.length > 0 && (
          <Badge tone="danger">{issues.length} point(s) à corriger</Badge>
        )}
      </div>
    </form>
  )
}
