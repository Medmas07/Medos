import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CheckboxField,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
} from '@hackcure/design-system'
import { formatDate, formatDateTime, requestStatusDisplay } from '../presentation'
import {
  readinessChecks,
  submitAccessRequest,
  validateSubmission,
  type SubmissionDraft,
} from '../services/projectAccessRequest'
import { defaultDraftId, isEditableDraft } from '../services/projectCreation'
import { requestedVariables } from '../services/projectVariables'
import type { PageId, ProjectSummary, ResearchSnapshot } from '../types/research'

interface SubmitRequestViewProps {
  snapshot: ResearchSnapshot
  onUpdated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}

/** Research data-access request submission (HC-097): MOCKED, kept in session state. */
export function SubmitRequestView({ snapshot, onUpdated, onNavigate }: SubmitRequestViewProps) {
  const [selectedId, setSelectedId] = useState(() => defaultDraftId(snapshot))
  // The request submitted from this page, to confirm it once the project is locked.
  const [submittedId, setSubmittedId] = useState<string | null>(null)

  const header = (
    <PageHeader
      eyebrow="Projets et demandes · HC-097"
      title="Demande d'accès"
      description="Soumettre le projet complet à l'Autorité de gouvernance et d'éthique, seule habilitée à autoriser une exécution Compute-to-Data."
      actions={<DemoBadge>Soumission simulée</DemoBadge>}
    />
  )

  const summary = snapshot.projects.find((s) => s.project.id === selectedId) ?? snapshot.projects[0]
  if (!summary) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="Créez d'abord un projet pour préparer sa demande d'accès."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  const { project, request } = summary
  const requestStatus = requestStatusDisplay[request?.status ?? 'not_submitted']

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="La demande n'est transmise à personne">
          La demande est conservée dans cette page jusqu'à son rechargement : elle n'est pas transmise à l'Autorité de
          gouvernance, dont l'interface de recherche n'existe pas encore. Soumettre une demande n'autorise rien : seule
          une décision de l'Autorité peut permettre une exécution, et seuls des résultats agrégés contrôlés reviendront.
        </Alert>

        <Card>
          <SelectField
            label="Projet"
            value={project.id}
            onChange={(e) => setSelectedId(e.target.value)}
            options={snapshot.projects.map((s) => ({ value: s.project.id, label: `${s.project.id} · ${s.project.title}` }))}
          />
          <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
            {project.status === 'draft' && <Badge tone="neutral">Brouillon</Badge>}
            <span>Demande d'accès :</span>
            <Badge tone={requestStatus.tone}>{requestStatus.label}</Badge>
          </p>
        </Card>

        {isEditableDraft(summary) ? (
          // Resets the form when another project is selected.
          <SubmissionForm
            key={project.id}
            snapshot={snapshot}
            summary={summary}
            onSubmitted={(next, requestId) => {
              setSubmittedId(requestId)
              onUpdated(next)
            }}
            onNavigate={onNavigate}
          />
        ) : (
          <SubmittedRequest summary={summary} justSubmitted={request?.id === submittedId} onNavigate={onNavigate} />
        )}
      </div>
    </>
  )
}

function SubmittedRequest({
  summary,
  justSubmitted,
  onNavigate,
}: {
  summary: ProjectSummary
  justSubmitted: boolean
  onNavigate: (page: PageId) => void
}) {
  const { request, decision, authorized } = summary
  if (!request) return null
  const expired = request.status === 'approved' && !authorized
  const status = requestStatusDisplay[expired ? 'expired' : request.status]

  return (
    <>
      {justSubmitted ? (
        <Alert
          tone="success"
          title={`Demande ${request.id} soumise`}
          actions={<Button onClick={() => onNavigate('request-status')}>Suivre la demande</Button>}
        >
          Le projet est en revue : protocole, population, variables et établissements ne peuvent plus être modifiés.
          Aucune exécution n'est possible avant une décision favorable de l'Autorité de gouvernance.
        </Alert>
      ) : (
        <Alert tone="neutral" title="Demande déjà soumise">
          La demande d'accès de ce projet a été soumise : le projet est examiné tel qu'il a été soumis et ne peut plus
          être modifié.
          {expired && " Son autorisation a expiré ; une nouvelle demande pour ce projet n'est pas encore possible dans cette démonstration."}
        </Alert>
      )}
      <Card title="Demande soumise">
        <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Référence</dt>
            <dd className="font-medium text-slate-900">{request.id}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Soumise le</dt>
            <dd className="font-medium text-slate-900">{formatDateTime(request.submittedAt)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Statut</dt>
            <dd>
              <Badge tone={status.tone}>{status.label}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Décision de l'Autorité de gouvernance</dt>
            <dd className="font-medium text-slate-900">
              {decision
                ? `${decision.outcome === 'approved' ? 'Approuvée' : 'Refusée'} le ${formatDate(decision.decidedAt)}`
                : 'Attendue'}
            </dd>
          </div>
        </dl>
        {!justSubmitted && (
          <div className="mt-4">
            <Button variant="secondary" onClick={() => onNavigate('request-status')}>
              Suivre la demande
            </Button>
          </div>
        )}
      </Card>
    </>
  )
}

function SubmissionForm({
  snapshot,
  summary,
  onSubmitted,
  onNavigate,
}: {
  snapshot: ResearchSnapshot
  summary: ProjectSummary
  onSubmitted: (snapshot: ResearchSnapshot, requestId: string) => void
  onNavigate: (page: PageId) => void
}) {
  const { project } = summary
  const [draft, setDraft] = useState<SubmissionDraft>({ acknowledged: false })
  // Errors are shown once the researcher has tried to submit.
  const [showErrors, setShowErrors] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  const checks = readinessChecks(summary)
  const allErrors = validateSubmission(summary, draft)
  const errors = showErrors ? allErrors : {}
  const variables = requestedVariables(project).entries

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setShowErrors(true)
    setFailure(null)
    if (Object.keys(allErrors).length > 0) return
    setSubmitting(true)
    try {
      const { request, snapshot: next } = await submitAccessRequest(snapshot, project.id, draft)
      onSubmitted(next, request.id)
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error))
      setSubmitting(false)
    }
  }

  return (
    <>
      {failure && (
        <Alert tone="danger" title="La demande n'a pas été soumise">
          {failure}
        </Alert>
      )}

      <Card title="Éléments requis par l'Autorité de gouvernance">
        <ul className="divide-y divide-slate-200">
          {checks.map((check) => (
            <li key={check.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="space-y-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{check.label}</span>
                  <Badge tone={check.ready ? 'success' : 'warning'}>{check.ready ? 'Prêt' : 'À compléter'}</Badge>
                </div>
                <p className="text-sm text-slate-600">{check.detail}</p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => onNavigate(check.page)} disabled={submitting}>
                {check.ready ? 'Revoir' : 'Compléter'}
              </Button>
            </li>
          ))}
        </ul>
        {errors.checks && (
          <p role="alert" className="mt-3 text-sm font-medium text-danger-700">
            {errors.checks}
          </p>
        )}
      </Card>

      <Card title="Récapitulatif de la demande">
        <form noValidate onSubmit={submit} className="space-y-5">
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-slate-500">Projet</dt>
              <dd className="font-medium text-slate-900">{project.title}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Objectif scientifique</dt>
              <dd className="text-slate-800">{project.summary}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Population</dt>
              <dd className="text-slate-800">{project.population || '—'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Variables</dt>
              <dd className="text-slate-800">{variables.map((v) => v.label).join(', ') || '—'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Établissements</dt>
              <dd className="text-slate-800">
                {summary.participatingOrganizations.map((o) => o.shortName).join(', ') || '—'}
              </dd>
            </div>
          </dl>

          <CheckboxField
            label="Je soumets cette demande en tant que chercheur principal"
            hint="Je comprends qu'elle n'autorise rien par elle-même, que l'Autorité de gouvernance peut la refuser ou n'en autoriser qu'une partie, qu'aucune donnée brute ne quittera les Hospital Nodes et que le projet ne pourra plus être modifié une fois soumis."
            checked={draft.acknowledged}
            onChange={(e) => setDraft({ acknowledged: e.target.checked })}
            error={errors.acknowledged}
            disabled={submitting}
          />

          <Button type="submit" loading={submitting}>
            Soumettre la demande d'accès
          </Button>
        </form>
      </Card>
    </>
  )
}
