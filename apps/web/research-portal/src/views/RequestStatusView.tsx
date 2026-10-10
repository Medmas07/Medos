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
import {
  authorizationDisplay,
  formatDate,
  formatDateTime,
  requestStateDisplay,
  stepStateTone,
  trackingStepLabels,
} from '../presentation'
import { deriveRequestTracking, type RequestState, type TrackedRequest } from '../services/requestTracking'
import type { PageId, ResearchSnapshot } from '../types/research'

interface RequestStatusViewProps {
  snapshot: ResearchSnapshot
  onNavigate: (page: PageId) => void
}

const STATE_ORDER: readonly RequestState[] = ['rejected', 'expired', 'expiring', 'under_review', 'approved']

function stepItems({ steps, state, transmitted }: TrackedRequest): TimelineItem[] {
  return steps.map((step) => {
    let description: string | undefined
    if (step.id === 'review' && step.state === 'current') {
      description = transmitted
        ? "La demande est examinée : protocole, population, variables et établissements, tels qu'ils ont été soumis."
        : "Cette demande n'a pas été transmise : aucun examen n'a lieu dans cette démonstration."
    }
    if (step.id === 'decision' && step.state === 'blocked') {
      description = state === 'rejected' ? 'Demande refusée.' : 'Autorisation expirée : aucune nouvelle exécution possible.'
    }
    return {
      id: step.id,
      title: trackingStepLabels[step.id],
      timestamp: step.at ? formatDateTime(step.at) : { done: 'Terminé', current: 'En cours', blocked: '—', upcoming: 'À venir' }[step.state],
      dateTime: step.at ?? undefined,
      description,
      tone: stepStateTone[step.state],
      current: step.state === 'current',
    }
  })
}

function Decision({ tracked }: { tracked: TrackedRequest }) {
  const { decision, decidedBy, authorization } = tracked
  if (!decision) return null
  return (
    <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
      <div>
        <dt className="text-slate-500">Décision</dt>
        <dd className="font-medium text-slate-900">
          {decision.id} · {decision.outcome === 'approved' ? 'approuvée' : 'refusée'} le {formatDate(decision.decidedAt)}
        </dd>
      </div>
      <div>
        <dt className="text-slate-500">Décidée par</dt>
        <dd className="font-medium text-slate-900">
          {decidedBy ? `${decidedBy.title ?? ''} ${decidedBy.firstName} ${decidedBy.lastName}`.trim() : decision.decidedById}
          <span className="block text-xs font-normal text-slate-500">Autorité de gouvernance et d'éthique</span>
        </dd>
      </div>
      <div className="sm:col-span-2">
        <dt className="text-slate-500">Motivation</dt>
        <dd className="text-slate-800">{decision.rationale}</dd>
      </div>
      {decision.conditions.length > 0 && (
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Conditions</dt>
          <dd>
            <ul className="list-disc space-y-0.5 pl-4 text-slate-800">
              {decision.conditions.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </dd>
        </div>
      )}
      {authorization && (
        <div>
          <dt className="text-slate-500">Validité</dt>
          <dd className="flex flex-wrap items-center gap-2">
            <Badge tone={authorizationDisplay[authorization.state].tone}>
              {authorizationDisplay[authorization.state].label}
            </Badge>
            <span className="text-slate-600">
              {decision.validUntil
                ? authorization.state === 'expired'
                  ? `depuis le ${formatDate(decision.validUntil)}`
                  : `jusqu'au ${formatDate(decision.validUntil)} (${authorization.daysLeft} j)`
                : 'Sans échéance'}
            </span>
          </dd>
        </div>
      )}
    </dl>
  )
}

function NextStep({ tracked, onNavigate }: { tracked: TrackedRequest; onNavigate: (page: PageId) => void }) {
  switch (tracked.state) {
    case 'under_review':
      return (
        <p className="text-slate-600">
          En attente de la décision de l'Autorité de gouvernance. Ni ce portail ni l'opérateur de la plateforme ne
          peuvent l'autoriser ; aucune exécution n'est possible d'ici là.
        </p>
      )
    case 'rejected':
    case 'expired':
      return (
        <p className="text-slate-600">
          Aucune exécution n'est possible pour ce projet. Une nouvelle demande pour un projet déjà soumis n'est pas
          encore possible dans cette démonstration.
        </p>
      )
    default:
      return (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-slate-600">
            Le code peut être envoyé aux Hospital Nodes autorisés ; seuls des résultats agrégés contrôlés reviendront.
          </p>
          <Button variant="secondary" onClick={() => onNavigate('workspace')}>
            Ouvrir l'espace de travail
          </Button>
        </div>
      )
  }
}

function RequestCard({ tracked, onNavigate }: { tracked: TrackedRequest; onNavigate: (page: PageId) => void }) {
  const { summary, request, state, transmitted } = tracked
  const display = requestStateDisplay[state]
  return (
    <Card
      title={summary.project.title}
      description={`${request.id} · ${summary.project.id} · ${
        summary.participatingOrganizations.map((o) => o.shortName).join(', ') || 'aucun établissement'
      }`}
      actions={<Badge tone={display.tone}>{display.label}</Badge>}
    >
      <div className="space-y-5">
        {!transmitted && (
          <Alert tone="demo" title="Demande non transmise">
            Soumise dans cette session, elle reste dans ce portail jusqu'à son rechargement : l'interface de recherche
            du Governance Node n'existe pas encore, donc aucune décision ne peut la suivre.
          </Alert>
        )}
        <Timeline label={`Suivi de la demande ${request.id}`} items={stepItems(tracked)} />
        <Decision tracked={tracked} />
        <div className="border-t border-slate-200 pt-4">
          <NextStep tracked={tracked} onNavigate={onNavigate} />
        </div>
      </div>
    </Card>
  )
}

/** Research request tracking (HC-098): status and Governance decision of each access request, displayed only. */
export function RequestStatusView({ snapshot, onNavigate }: RequestStatusViewProps) {
  const tracking = deriveRequestTracking(snapshot)

  const header = (
    <PageHeader
      eyebrow="Projets et demandes · HC-098"
      title="Suivi des demandes"
      description={`Statut des demandes d'accès et décisions de l'Autorité de gouvernance, au ${formatDateTime(snapshot.asOf)}.`}
      actions={<DemoBadge>Décisions fictives</DemoBadge>}
    />
  )

  if (snapshot.projects.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="Créez un projet, puis soumettez sa demande d'accès pour la suivre ici."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Décisions affichées uniquement">
          Les statuts et décisions proviennent des données fictives. Ce portail ne peut ni enregistrer, ni modifier, ni
          accélérer une décision : seule l'Autorité de gouvernance et d'éthique décide, et elle peut refuser une demande
          ou n'en autoriser qu'une partie.
        </Alert>

        {tracking.requests.length === 0 ? (
          <Card>
            <EmptyState
              title="Aucune demande soumise"
              description="Une demande apparaît ici dès sa soumission à l'Autorité de gouvernance."
              action={<Button onClick={() => onNavigate('submit-request')}>Préparer une demande</Button>}
            />
          </Card>
        ) : (
          <>
            <ul aria-label="Demandes par statut" className="flex flex-wrap gap-2">
              {STATE_ORDER.filter((s) => tracking.counts[s] > 0).map((s) => (
                <li key={s}>
                  <Badge tone={requestStateDisplay[s].tone}>
                    {requestStateDisplay[s].label} : {tracking.counts[s]}
                  </Badge>
                </li>
              ))}
            </ul>
            {tracking.requests.map((tracked) => (
              <RequestCard key={tracked.request.id} tracked={tracked} onNavigate={onNavigate} />
            ))}
          </>
        )}

        {tracking.unsubmitted.length > 0 && (
          <Card title="Projets sans demande d'accès" description="Ces projets n'ont pas encore été soumis.">
            <ul className="divide-y divide-slate-200">
              {tracking.unsubmitted.map(({ project }) => (
                <li key={project.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900">{project.title}</p>
                    <p className="text-xs text-slate-500">
                      {project.id} · créé le {formatDate(project.createdAt)}
                    </p>
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => onNavigate('submit-request')}>
                    Préparer la demande
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </>
  )
}
