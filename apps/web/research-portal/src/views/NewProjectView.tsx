import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  PageHeader,
  TextareaField,
  TextField,
} from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import {
  createResearchProject,
  SUMMARY_MAX,
  TITLE_MAX,
  validateProjectDraft,
  type ProjectDraft,
  type ProjectDraftErrors,
} from '../services/projectCreation'
import type { PageId, ResearchProject, ResearchSnapshot } from '../types/research'

interface NewProjectViewProps {
  snapshot: ResearchSnapshot
  onCreated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}

const EMPTY_DRAFT: ProjectDraft = { title: '', summary: '' }

/** Steps that complete a draft before its access request, each delivered by its own ticket. */
const NEXT_STEPS: { page: PageId; label: string; ticket: string }[] = [
  { page: 'protocol', label: 'Déposer le protocole et les documents', ticket: 'HC-093' },
  { page: 'population', label: 'Définir la population étudiée', ticket: 'HC-094' },
  { page: 'variables', label: 'Définir les variables demandées', ticket: 'HC-095' },
  { page: 'hospitals', label: 'Choisir les établissements participants', ticket: 'HC-096' },
  { page: 'submit-request', label: "Soumettre la demande d'accès à l'Autorité de gouvernance", ticket: 'HC-097' },
]

function CreatedProjectCard({
  project,
  onNavigate,
  onRestart,
}: {
  project: ResearchProject
  onNavigate: (page: PageId) => void
  onRestart: () => void
}) {
  return (
    <>
      <Alert tone="success" title="Projet créé en brouillon" className="mb-6">
        {project.id} est enregistré pour cette session de démonstration uniquement : il disparaît au
        rechargement de la page. Aucune donnée n'est demandée tant que la demande d'accès n'est pas
        soumise et autorisée par l'Autorité de gouvernance.
      </Alert>
      <Card
        title={project.title}
        description={`${project.id} · créé le ${formatDateTime(project.createdAt)}`}
        actions={<Badge tone="neutral">Brouillon</Badge>}
      >
        <p className="text-slate-700">{project.summary}</p>
        <h2 className="mt-5 font-semibold text-slate-900">Étapes suivantes</h2>
        <ol className="mt-2 divide-y divide-slate-200">
          {NEXT_STEPS.map((step, index) => (
            <li key={step.page} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="text-slate-800">
                {index + 1}. {step.label}
              </span>
              <Button variant="ghost" size="sm" onClick={() => onNavigate(step.page)}>
                Ouvrir ({step.ticket})
              </Button>
            </li>
          ))}
        </ol>
        <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-200 pt-4">
          <Button onClick={() => onNavigate('dashboard')}>Voir le tableau de bord</Button>
          <Button variant="secondary" onClick={onRestart}>
            Créer un autre projet
          </Button>
        </div>
      </Card>
    </>
  )
}

/** Research project creation (HC-092): a MOCKED draft held in session state. */
export function NewProjectView({ snapshot, onCreated, onNavigate }: NewProjectViewProps) {
  const [draft, setDraft] = useState<ProjectDraft>(EMPTY_DRAFT)
  // Errors are shown once the researcher has tried to submit.
  const [showErrors, setShowErrors] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [created, setCreated] = useState<ResearchProject | null>(null)

  const { researcher, organization } = snapshot
  const errors: ProjectDraftErrors = showErrors
    ? validateProjectDraft(draft, snapshot.projects.map((s) => s.project))
    : {}

  const update = (field: keyof ProjectDraft) => (value: string) => setDraft((d) => ({ ...d, [field]: value }))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setShowErrors(true)
    setFailure(null)
    if (Object.keys(validateProjectDraft(draft, snapshot.projects.map((s) => s.project))).length > 0) return
    setSubmitting(true)
    try {
      const result = await createResearchProject(snapshot, draft)
      setCreated(result.project)
      onCreated(result.snapshot)
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error))
    } finally {
      setSubmitting(false)
    }
  }

  const restart = () => {
    setDraft(EMPTY_DRAFT)
    setShowErrors(false)
    setCreated(null)
  }

  return (
    <>
      <PageHeader
        eyebrow="Projets et demandes · HC-092"
        title="Nouveau projet"
        description="Créez le projet en brouillon, puis complétez-le avant de soumettre la demande d'accès."
        actions={<DemoBadge>Création simulée</DemoBadge>}
      />

      {created ? (
        <CreatedProjectCard project={created} onNavigate={onNavigate} onRestart={restart} />
      ) : (
        <>
          <Alert tone="info" title="Créer un projet ne donne accès à aucune donnée" className="mb-6">
            Le projet reste un brouillon jusqu'à la soumission de sa demande d'accès. Seule l'Autorité de
            gouvernance et d'éthique peut l'autoriser ; les analyses seront ensuite exécutées dans les
            Hospital Nodes, sans export de données individuelles.
          </Alert>

          {failure && (
            <Alert tone="danger" title="Le projet n'a pas été créé" className="mb-6">
              {failure}
            </Alert>
          )}

          <Card title="Informations du projet">
            <form noValidate onSubmit={submit} className="space-y-5">
              <TextField
                label="Titre du projet"
                required
                maxLength={TITLE_MAX}
                value={draft.title}
                onChange={(e) => update('title')(e.target.value)}
                error={errors.title}
                hint="Un titre court et explicite, unique parmi vos projets."
                disabled={submitting}
              />
              <TextareaField
                label="Objectif scientifique"
                required
                rows={5}
                maxLength={SUMMARY_MAX}
                value={draft.summary}
                onChange={(e) => update('summary')(e.target.value)}
                error={errors.summary}
                hint={`La question de recherche et ce que le projet cherche à décrire ou mesurer (${draft.summary.trim().length}/${SUMMARY_MAX}).`}
                disabled={submitting}
              />
              <dl className="grid gap-4 rounded-md bg-slate-50 p-4 sm:grid-cols-3">
                <div>
                  <dt className="text-xs text-slate-500">Chercheur principal</dt>
                  <dd className="font-medium text-slate-900">
                    {researcher.title} {researcher.firstName} {researcher.lastName}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Organisation</dt>
                  <dd className="font-medium text-slate-900">{organization.name}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Statut à la création</dt>
                  <dd>
                    <Badge tone="neutral">Brouillon</Badge>
                  </dd>
                </div>
              </dl>
              <div className="flex flex-wrap gap-2">
                <Button type="submit" loading={submitting}>
                  Créer le projet
                </Button>
                <Button variant="secondary" type="button" onClick={() => onNavigate('dashboard')} disabled={submitting}>
                  Annuler
                </Button>
              </div>
            </form>
          </Card>
        </>
      )}
    </>
  )
}
