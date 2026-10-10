import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  TextareaField,
  TextField,
  type Tone,
} from '@hackcure/design-system'
import { formatDate, requestStatusDisplay } from '../presentation'
import { defaultDraftId, isEditableDraft } from '../services/projectCreation'
import {
  AGE_MAX,
  criteriaFromDraft,
  DESCRIPTION_MAX,
  draftFromProject,
  populationStatus,
  savePopulation,
  validatePopulationDraft,
  type PopulationDraft,
  type PopulationStatus,
} from '../services/projectPopulation'
import type { PageId, PopulationCriteria, ResearchProject, ResearchSnapshot } from '../types/research'

interface PopulationViewProps {
  snapshot: ResearchSnapshot
  onUpdated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}

const statusDisplay: Record<PopulationStatus, { label: string; tone: Tone }> = {
  defined: { label: 'Définie', tone: 'success' },
  described: { label: 'Décrite', tone: 'success' },
  missing: { label: 'À définir', tone: 'warning' },
}

/** French sentences for the criteria, in the order a Hospital Node applies them. */
function describeCriteria(criteria: PopulationCriteria): string[] {
  const { ageMin, ageMax, encounterFrom, encounterTo } = criteria
  const lines: string[] = []
  if (ageMin !== undefined && ageMax !== undefined) lines.push(`Âge de ${ageMin} à ${ageMax} ans`)
  else if (ageMin !== undefined) lines.push(`Âge de ${ageMin} ans ou plus`)
  else if (ageMax !== undefined) lines.push(`Âge de ${ageMax} ans ou moins`)
  if (encounterFrom && encounterTo)
    lines.push(`Au moins une consultation du ${formatDate(encounterFrom)} au ${formatDate(encounterTo)}`)
  else if (encounterFrom) lines.push(`Au moins une consultation depuis le ${formatDate(encounterFrom)}`)
  else if (encounterTo) lines.push(`Au moins une consultation jusqu'au ${formatDate(encounterTo)}`)
  return lines
}

function CriteriaList({ criteria }: { criteria: PopulationCriteria }) {
  return (
    <ul className="list-disc space-y-1 pl-5 text-slate-800">
      {describeCriteria(criteria).map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  )
}

/** Research population definition (HC-094): MOCKED, saved on the draft in session state. */
export function PopulationView({ snapshot, onUpdated, onNavigate }: PopulationViewProps) {
  const [selectedId, setSelectedId] = useState(() => defaultDraftId(snapshot))

  const header = (
    <PageHeader
      eyebrow="Projets et demandes · HC-094"
      title="Population étudiée"
      description="Les personnes dont les données seront analysées, examinées par l'Autorité de gouvernance et d'éthique avec la demande d'accès."
      actions={<DemoBadge>Enregistrement simulé</DemoBadge>}
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
            description="Créez d'abord un projet pour définir sa population."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  const { project, request } = summary
  const editable = isEditableDraft(summary)
  const status = statusDisplay[populationStatus(project)]
  const requestStatus = requestStatusDisplay[request?.status ?? 'not_submitted']

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Aucun patient n'est compté ni sélectionné">
          La population est une définition : après autorisation, chaque Hospital Node participant l'applique
          localement à ses propres données, et ni la liste des patients ni leur nombre ne reviennent au portail.
          L'enregistrement est conservé dans cette page jusqu'à son rechargement.
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
            <span>Population :</span>
            <Badge tone={status.tone}>{status.label}</Badge>
            <span>Demande d'accès :</span>
            <Badge tone={requestStatus.tone}>{requestStatus.label}</Badge>
          </p>
        </Card>

        {editable ? (
          // Resets the form when another project is selected.
          <PopulationForm key={project.id} snapshot={snapshot} project={project} onUpdated={onUpdated} onNavigate={onNavigate} />
        ) : (
          <>
            <Alert tone="neutral" title="Population verrouillée">
              La demande d'accès de ce projet a été soumise à l'Autorité de gouvernance : sa population est examinée
              telle qu'elle a été définie et ne peut plus être modifiée.
            </Alert>
            <Card title="Population soumise">
              <p className="text-slate-700">{project.population || 'Aucune population décrite.'}</p>
              <div className="mt-4 border-t border-slate-200 pt-4">
                <h2 className="mb-2 font-semibold text-slate-900">Critères d'éligibilité</h2>
                {project.populationCriteria ? (
                  <CriteriaList criteria={project.populationCriteria} />
                ) : (
                  <p className="text-sm text-slate-500">
                    Critères non structurés : ce projet de démonstration ne contient que la description.
                  </p>
                )}
              </div>
            </Card>
          </>
        )}
      </div>
    </>
  )
}

function PopulationForm({
  snapshot,
  project,
  onUpdated,
  onNavigate,
}: {
  snapshot: ResearchSnapshot
  project: ResearchProject
  onUpdated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}) {
  const [draft, setDraft] = useState<PopulationDraft>(() => draftFromProject(project))
  // Errors are shown once the researcher has tried to save.
  const [showErrors, setShowErrors] = useState(false)
  const [saving, setSaving] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const allErrors = validatePopulationDraft(draft)
  const errors = showErrors ? allErrors : {}
  // Preview only the criteria whose fields are valid.
  const preview = criteriaFromDraft({
    ...draft,
    ageMin: allErrors.ageMin ? '' : draft.ageMin,
    ageMax: allErrors.ageMax || allErrors.ageMin ? '' : draft.ageMax,
    encounterFrom: allErrors.encounterFrom ? '' : draft.encounterFrom,
    encounterTo: allErrors.encounterTo || allErrors.encounterFrom ? '' : draft.encounterTo,
  })

  const update = (field: keyof PopulationDraft) => (value: string) => {
    setDraft((d) => ({ ...d, [field]: value }))
    setSaved(false)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setShowErrors(true)
    setFailure(null)
    if (Object.keys(allErrors).length > 0) return
    setSaving(true)
    try {
      onUpdated(await savePopulation(snapshot, project.id, draft))
      setSaved(true)
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      {saved && (
        <Alert
          tone="success"
          title="Population enregistrée"
          actions={<Button onClick={() => onNavigate('variables')}>Continuer : variables</Button>}
        >
          Définir la population ne donne accès à aucune donnée : elle sera examinée avec la demande d'accès (HC-097).
        </Alert>
      )}
      {failure && (
        <Alert tone="danger" title="La population n'a pas été enregistrée">
          {failure}
        </Alert>
      )}

      <Card title="Définition de la population">
        <form noValidate onSubmit={submit} className="space-y-5">
          <TextareaField
            label="Description"
            required
            rows={3}
            maxLength={DESCRIPTION_MAX}
            value={draft.description}
            onChange={(e) => update('description')(e.target.value)}
            error={errors.description}
            hint={`Qui est étudié, en langage clair, tel que l'Autorité de gouvernance le lira (${draft.description.trim().length}/${DESCRIPTION_MAX}).`}
            disabled={saving}
          />

          <fieldset className="space-y-3">
            <legend className="font-medium text-slate-800">Tranche d'âge</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField
                label="Âge minimal (ans)"
                type="number"
                inputMode="numeric"
                min={0}
                max={AGE_MAX}
                value={draft.ageMin}
                onChange={(e) => update('ageMin')(e.target.value)}
                error={errors.ageMin}
                disabled={saving}
              />
              <TextField
                label="Âge maximal (ans)"
                type="number"
                inputMode="numeric"
                min={0}
                max={AGE_MAX}
                value={draft.ageMax}
                onChange={(e) => update('ageMax')(e.target.value)}
                error={errors.ageMax}
                disabled={saving}
              />
            </div>
          </fieldset>

          <fieldset className="space-y-3">
            <legend className="font-medium text-slate-800">Période de consultation</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField
                label="Du"
                type="date"
                value={draft.encounterFrom}
                onChange={(e) => update('encounterFrom')(e.target.value)}
                error={errors.encounterFrom}
                disabled={saving}
              />
              <TextField
                label="Au"
                type="date"
                value={draft.encounterTo}
                onChange={(e) => update('encounterTo')(e.target.value)}
                error={errors.encounterTo}
                disabled={saving}
              />
            </div>
            <p className="text-xs text-slate-500">
              Les personnes ayant au moins une consultation sur la période, bornes comprises.
            </p>
          </fieldset>

          {errors.criteria && (
            <p role="alert" className="text-sm font-medium text-danger-700">
              {errors.criteria}
            </p>
          )}

          <div className="rounded-md bg-slate-50 p-4">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Critères appliqués par chaque Hospital Node</h2>
            {Object.keys(preview).length > 0 ? (
              <CriteriaList criteria={preview} />
            ) : (
              <p className="text-sm text-slate-500">Aucun critère pour l'instant.</p>
            )}
            <p className="mt-2 text-xs text-slate-500">
              Seuls l'âge et la période de consultation peuvent être appliqués par les Hospital Nodes à ce stade ;
              précisez les autres conditions (diagnostic, traitement…) dans la description et le protocole.
            </p>
          </div>

          <Button type="submit" loading={saving}>
            Enregistrer la population
          </Button>
        </form>
      </Card>
    </>
  )
}
