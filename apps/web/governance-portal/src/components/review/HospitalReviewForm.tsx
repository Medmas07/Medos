import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  CheckboxField,
  DemoBadge,
  TextareaField,
} from '@hackcure/design-system'
import {
  InvalidReview,
  MIN_RATIONALE_LENGTH,
  emptyDraft,
  hasFindings,
  recordReview,
  reviewFindings,
  validateReview,
  type ReviewDraft,
  type ReviewField,
  type ReviewIssue,
} from '../../services/hospitalReview'
import { reviewStore } from '../../services/reviewStore'
import type { HospitalApplication, PersonInfo } from '../../types/governance'

/** Simulated round trip to the Governance Node; the real API (HC-131) is PLANNED. */
const SIMULATED_DELAY_MS = 900

type Step = 'editing' | 'confirming' | 'submitting'

interface HospitalReviewFormProps {
  application: HospitalApplication
  organizationName: string
  reviewer: PersonInfo | undefined
  reviewerName: string
}

function issueFor(issues: ReviewIssue[], field: ReviewField): string | undefined {
  return issues.find((i) => i.field === field)?.message
}

export function HospitalReviewForm({
  application,
  organizationName,
  reviewer,
  reviewerName,
}: HospitalReviewFormProps) {
  const [draft, setDraft] = useState<ReviewDraft>(emptyDraft)
  const [conditionsText, setConditionsText] = useState('')
  const [step, setStep] = useState<Step>('editing')
  const [showIssues, setShowIssues] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => () => clearTimeout(timer.current), [])

  const findings = reviewFindings(application)
  const currentDraft: ReviewDraft = { ...draft, conditions: conditionsText.split('\n') }
  const issues = validateReview(application, currentDraft, reviewer)
  const visibleIssues = showIssues ? issues : []
  const blocking = issues.filter((i) => i.field === 'application' || i.field === 'reviewer')

  const update = (changes: Partial<ReviewDraft>) => setDraft((d) => ({ ...d, ...changes }))

  const review = () => {
    setShowIssues(true)
    if (issues.length === 0) setStep('confirming')
  }

  const confirm = () => {
    setStep('submitting')
    timer.current = setTimeout(() => {
      try {
        reviewStore.record(
          recordReview(application, currentDraft, reviewer, new Date(), reviewStore.nextSequence()),
        )
      } catch (error) {
        if (!(error instanceof InvalidReview)) throw error
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

  const conditions = currentDraft.conditions.map((c) => c.trim()).filter(Boolean)

  if (step !== 'editing') {
    return (
      <div className="space-y-3">
        <Alert
          tone={draft.outcome === 'approved' ? 'success' : 'danger'}
          title={`Confirmer ${draft.outcome === 'approved' ? 'l’approbation' : 'le rejet'} de ${organizationName}`}
        >
          <p>« {draft.rationale.trim()} »</p>
          {conditions.length > 0 && (
            <ul className="mt-2 list-disc space-y-0.5 pl-4">
              {conditions.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs">
            Décision de {reviewerName}. Elle sera enregistrée dans l’état local du portail avec un
            événement d’audit, sans être transmise au Nœud de Gouvernance.
          </p>
        </Alert>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={draft.outcome === 'approved' ? 'primary' : 'danger'}
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
      className="space-y-4 text-sm"
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        review()
      }}
    >
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
          Décision du réviseur
        </h4>
        <DemoBadge>Simulé — HC-131 planifié</DemoBadge>
      </div>

      {hasFindings(findings) && (
        <div className="space-y-2 rounded-xl border border-warning-200 bg-warning-50 p-3 text-xs">
          <div className="font-semibold text-warning-800">Points à examiner avant de statuer</div>
          <ul className="list-disc space-y-1 pl-4 text-warning-800">
            {findings.missingDocuments.map((d) => (
              <li key={d.id}>Pièce manquante : {d.title}</li>
            ))}
            {findings.unacceptedAgreements.map((a) => (
              <li key={a.code}>Accord non accepté : {a.title}</li>
            ))}
            {findings.completenessFindings.map((f) => (
              <li key={`c-${f}`}>Contrôle de complétude : {f}</li>
            ))}
          </ul>
          {findings.advisoryFindings.length > 0 && (
            <div className="rounded border border-demo-200 bg-surface p-2">
              <div className="flex items-center gap-1.5 font-medium text-slate-800">
                Observations de l’IA <DemoBadge>Consultatif — non contraignant</DemoBadge>
              </div>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-slate-700">
                {findings.advisoryFindings.map((f) => (
                  <li key={`a-${f}`}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          <CheckboxField
            label="J’ai examiné chacun de ces points."
            hint="L’avis de l’IA ne remplace pas votre examen ; la décision vous appartient."
            checked={draft.findingsAcknowledged}
            onChange={(e) => update({ findingsAcknowledged: e.target.checked })}
            error={issueFor(visibleIssues, 'acknowledgement')}
          />
        </div>
      )}

      <fieldset className="space-y-1.5">
        <legend className="font-medium text-slate-800">
          Décision<span aria-hidden="true" className="ml-0.5 text-danger-700">*</span>
        </legend>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={draft.outcome === 'approved' ? 'primary' : 'secondary'}
            aria-pressed={draft.outcome === 'approved'}
            onClick={() => update({ outcome: 'approved' })}
          >
            Approuver
          </Button>
          <Button
            type="button"
            size="sm"
            variant={draft.outcome === 'rejected' ? 'danger' : 'secondary'}
            aria-pressed={draft.outcome === 'rejected'}
            onClick={() => update({ outcome: 'rejected' })}
          >
            Rejeter
          </Button>
        </div>
        {issueFor(visibleIssues, 'outcome') && (
          <p className="text-xs font-medium text-danger-700">{issueFor(visibleIssues, 'outcome')}</p>
        )}
      </fieldset>

      <TextareaField
        label="Motivation"
        required
        rows={3}
        value={draft.rationale}
        onChange={(e) => update({ rationale: e.target.value })}
        hint={`Au moins ${MIN_RATIONALE_LENGTH} caractères. Elle figurera dans la décision.`}
        error={issueFor(visibleIssues, 'rationale')}
      />

      {draft.outcome === 'approved' && (
        <TextareaField
          label="Conditions"
          rows={2}
          value={conditionsText}
          onChange={(e) => setConditionsText(e.target.value)}
          placeholder="Fournir l’attestation d’assurance avant la mise en service du nœud."
          hint="Une condition par ligne. Obligatoire si le dossier est incomplet."
          error={issueFor(visibleIssues, 'conditions')}
        />
      )}

      <div className="flex items-center gap-2">
        <Button type="submit">Vérifier la décision</Button>
        {showIssues && issues.length > 0 && (
          <Badge tone="danger">{issues.length} point(s) à corriger</Badge>
        )}
      </div>
    </form>
  )
}
