import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  CheckboxField,
  DemoBadge,
  TextareaField,
  TextField,
} from '@hackcure/design-system'
import { MIN_RATIONALE_LENGTH } from '../../services/hospitalReview'
import {
  InvalidResearchReview,
  MAX_VALIDITY_MONTHS,
  MINIMUM_CELL_SIZE_FLOOR,
  initialResearchDraft,
  isEligibleOrganization,
  recordResearchReview,
  researchChecks,
  validUntil,
  validateResearchReview,
  type ResearchReviewContext,
  type ResearchReviewDraft,
  type ResearchReviewField,
  type ResearchReviewIssue,
} from '../../services/researchReview'
import { reviewStore } from '../../services/reviewStore'
import type { PersonInfo } from '../../types/governance'

/** Simulated round trip to the Governance Node; the real API (HC-133) is PLANNED. */
const SIMULATED_DELAY_MS = 900

type Step = 'editing' | 'confirming' | 'submitting'

interface ResearchReviewFormProps {
  /** Everything but the time: the form reads the clock itself. */
  context: Omit<ResearchReviewContext, 'now'>
  reviewer: PersonInfo | undefined
  reviewerName: string
}

function issueFor(issues: ResearchReviewIssue[], field: ResearchReviewField): string | undefined {
  return issues.find((i) => i.field === field)?.message
}

const toggle = (values: string[], value: string, on: boolean) =>
  on ? [...values, value] : values.filter((v) => v !== value)

const formatDate = (date: Date) => date.toLocaleDateString('fr-TN')

export function ResearchReviewForm({ context: request, reviewer, reviewerName }: ResearchReviewFormProps) {
  // Checks and dates use the time the form opened; the decision is dated when confirmed.
  const [openedAt] = useState(() => new Date())
  const context: ResearchReviewContext = { ...request, now: openedAt }
  const [draft, setDraft] = useState<ResearchReviewDraft>(() => initialResearchDraft(context))
  const [conditionsText, setConditionsText] = useState('')
  const [step, setStep] = useState<Step>('editing')
  const [showIssues, setShowIssues] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => () => clearTimeout(timer.current), [])

  const project = context.project
  const checks = researchChecks(context)
  const approvalBlocked = checks.some((c) => c.state === 'fail')
  const currentDraft: ResearchReviewDraft = { ...draft, conditions: conditionsText.split('\n') }
  const issues = validateResearchReview(context, currentDraft, reviewer)
  const visibleIssues = showIssues ? issues : []
  const blocking = issues.filter((i) => i.field === 'request' || i.field === 'reviewer')
  const validMonths = Number.isInteger(draft.validityMonths) && draft.validityMonths >= 1
  const approving = draft.outcome === 'approved'

  const update = (changes: Partial<ResearchReviewDraft>) => setDraft((d) => ({ ...d, ...changes }))

  const review = () => {
    setShowIssues(true)
    if (issues.length === 0) setStep('confirming')
  }

  const confirm = () => {
    setStep('submitting')
    timer.current = setTimeout(() => {
      try {
        reviewStore.recordResearch(
          recordResearchReview(
            { ...context, now: new Date() },
            currentDraft,
            reviewer,
            reviewStore.nextSequence(),
          ),
        )
      } catch (error) {
        if (!(error instanceof InvalidResearchReview)) throw error
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

  if (step !== 'editing') {
    const name = (id: string) => context.organization(id)?.shortName ?? id
    return (
      <div className="space-y-3 text-xs">
        <Alert
          tone={approving ? 'success' : 'danger'}
          title={`${approving ? 'Approuver' : 'Rejeter'} la demande ${context.request.id}`}
        >
          <p>« {draft.rationale.trim()} »</p>
          {approving && (
            <ul className="mt-1 list-disc space-y-0.5 pl-4">
              <li>Compute-to-data uniquement, jusqu’au {formatDate(validUntil(openedAt, draft.validityMonths))}.</li>
              <li>Établissements : {draft.approvedOrganizationIds.map(name).join(', ')}.</li>
              <li>Variables : {draft.approvedVariables.join(', ')}.</li>
              <li>Effectif minimal de {draft.minimumCellSize} par cellule.</li>
            </ul>
          )}
          <p className="mt-2">
            Décision de {reviewerName}. Elle sera enregistrée dans l’état local du portail avec un
            événement d’audit, sans être transmise au Nœud de Gouvernance, au service de recherche
            ni aux nœuds hospitaliers.
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
        <h4 className="font-semibold uppercase tracking-wider text-slate-600">Avis du comité éthique</h4>
        <DemoBadge>Simulé — HC-133 planifié</DemoBadge>
      </div>

      <ul className="space-y-2" aria-label="Contrôles préalables">
        {checks.map((check) => (
          <li key={check.id} className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-slate-800">{check.label}</span>
              <Badge tone={check.state === 'pass' ? 'success' : 'danger'} dot>
                {check.state === 'pass' ? 'Conforme' : 'Non conforme'}
              </Badge>
            </div>
            <p className="mt-1 text-slate-600">{check.detail}</p>
          </li>
        ))}
      </ul>

      {approvalBlocked && (
        <Alert tone="warning" title="Approbation impossible">
          Un contrôle n’est pas conforme : seul un rejet motivé peut être enregistré.
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
          <p className="font-medium text-danger-700">{issueFor(visibleIssues, 'outcome')}</p>
        )}
        {issueFor(visibleIssues, 'checks') && (
          <p className="font-medium text-danger-700">{issueFor(visibleIssues, 'checks')}</p>
        )}
      </fieldset>

      {approving && project && (
        <>
          <fieldset className="space-y-2 rounded-xl border border-slate-200 p-3">
            <legend className="px-1 font-medium text-slate-800">Établissements autorisés</legend>
            {project.participatingOrganizationIds.map((id) => {
              const org = context.organization(id)
              const eligible = isEligibleOrganization(org)
              const disconnected = org?.node?.dmiState === 'disconnected'
              return (
                <CheckboxField
                  key={id}
                  label={org?.name ?? id}
                  hint={
                    !eligible
                      ? 'Non agréé ou sans nœud : ne peut pas être autorisé.'
                      : disconnected
                        ? 'DMI actuellement déconnecté : l’exécution pourra y être indisponible.'
                        : undefined
                  }
                  disabled={!eligible}
                  checked={draft.approvedOrganizationIds.includes(id)}
                  onChange={(e) =>
                    update({ approvedOrganizationIds: toggle(draft.approvedOrganizationIds, id, e.target.checked) })
                  }
                />
              )
            })}
            {issueFor(visibleIssues, 'organizations') && (
              <p className="font-medium text-danger-700">{issueFor(visibleIssues, 'organizations')}</p>
            )}
          </fieldset>

          <fieldset className="space-y-2 rounded-xl border border-slate-200 p-3">
            <legend className="px-1 font-medium text-slate-800">Variables autorisées</legend>
            <p className="text-slate-500">Décochez toute variable non nécessaire à la finalité du protocole.</p>
            {project.variables.map((variable) => (
              <CheckboxField
                key={variable}
                label={variable}
                checked={draft.approvedVariables.includes(variable)}
                onChange={(e) =>
                  update({ approvedVariables: toggle(draft.approvedVariables, variable, e.target.checked) })
                }
              />
            ))}
            {issueFor(visibleIssues, 'variables') && (
              <p className="font-medium text-danger-700">{issueFor(visibleIssues, 'variables')}</p>
            )}
          </fieldset>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <TextField
              label="Durée (mois)"
              type="number"
              min={1}
              max={MAX_VALIDITY_MONTHS}
              step={1}
              required
              value={Number.isNaN(draft.validityMonths) ? '' : draft.validityMonths}
              onChange={(e) => update({ validityMonths: e.target.valueAsNumber })}
              hint={`1 à ${MAX_VALIDITY_MONTHS} mois. Fin : ${
                validMonths ? formatDate(validUntil(openedAt, draft.validityMonths)) : '—'
              }.`}
              error={issueFor(visibleIssues, 'validity')}
            />
            <TextField
              label="Effectif minimal par cellule"
              type="number"
              min={MINIMUM_CELL_SIZE_FLOOR}
              step={1}
              required
              value={Number.isNaN(draft.minimumCellSize) ? '' : draft.minimumCellSize}
              onChange={(e) => update({ minimumCellSize: e.target.valueAsNumber })}
              hint={`Au moins ${MINIMUM_CELL_SIZE_FLOOR}. Les cellules plus petites sont supprimées des résultats.`}
              error={issueFor(visibleIssues, 'cellSize')}
            />
          </div>

          <TextareaField
            label="Conditions supplémentaires"
            rows={2}
            value={conditionsText}
            onChange={(e) => setConditionsText(e.target.value)}
            placeholder="Publication des résultats après relecture par l’Autorité."
            hint="Facultatif. Une condition par ligne. L’exécution compute-to-data et l’absence de données individuelles en sortie sont toujours imposées."
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
