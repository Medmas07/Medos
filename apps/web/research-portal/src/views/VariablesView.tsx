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
  TextareaField,
  type Tone,
} from '@hackcure/design-system'
import { requestStatusDisplay } from '../presentation'
import { defaultDraftId, isEditableDraft } from '../services/projectCreation'
import {
  CATEGORY_LABELS,
  catalogEntries,
  draftFromProject,
  JUSTIFICATION_MAX,
  MAX_VARIABLES,
  requestedVariables,
  saveVariables,
  validateVariablesDraft,
  VARIABLE_CATALOG,
  variablesStatus,
  type CatalogVariable,
  type VariableCategory,
  type VariablesDraft,
  type VariablesStatus,
} from '../services/projectVariables'
import type { PageId, ResearchProject, ResearchSnapshot } from '../types/research'

interface VariablesViewProps {
  snapshot: ResearchSnapshot
  onUpdated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}

const statusDisplay: Record<VariablesStatus, { label: string; tone: Tone }> = {
  justified: { label: 'Justifiées', tone: 'success' },
  listed: { label: 'Listées', tone: 'success' },
  missing: { label: 'À définir', tone: 'warning' },
}

const CATEGORIES = Object.keys(CATEGORY_LABELS) as VariableCategory[]

function QuasiIdentifierBadge() {
  return <Badge tone="warning">Quasi-identifiant</Badge>
}

function VariableList({ variables }: { variables: CatalogVariable[] }) {
  return (
    <ul className="space-y-2">
      {variables.map((v) => (
        <li key={v.name} className="flex flex-wrap items-center gap-2 text-slate-800">
          <span className="font-medium">{v.label}</span>
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{v.name}</code>
          {v.quasiIdentifier && <QuasiIdentifierBadge />}
        </li>
      ))}
    </ul>
  )
}

/** Requested variables definition (HC-095): MOCKED catalog, saved on the draft in session state. */
export function VariablesView({ snapshot, onUpdated, onNavigate }: VariablesViewProps) {
  const [selectedId, setSelectedId] = useState(() => defaultDraftId(snapshot))

  const header = (
    <PageHeader
      eyebrow="Projets et demandes · HC-095"
      title="Variables demandées"
      description="Les données nécessaires à l'analyse, examinées par l'Autorité de gouvernance et d'éthique avec la demande d'accès."
      actions={<DemoBadge>Catalogue fictif</DemoBadge>}
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
            description="Créez d'abord un projet pour définir ses variables."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  const { project, request } = summary
  const editable = isEditableDraft(summary)
  const status = statusDisplay[variablesStatus(project)]
  const requestStatus = requestStatusDisplay[request?.status ?? 'not_submitted']
  const { entries, unmatched } = requestedVariables(project)

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Aucune donnée n'est transmise">
          Demander une variable ne donne accès à aucune donnée : après autorisation, le code d'analyse s'exécute dans
          chaque Hospital Node participant et seuls des résultats agrégés contrôlés reviennent. Le catalogue est
          fictif et la présence des variables dans les Hospital Nodes n'est pas vérifiée. L'enregistrement est conservé
          dans cette page jusqu'à son rechargement.
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
            <span>Variables :</span>
            <Badge tone={status.tone}>{status.label}</Badge>
            <span>Demande d'accès :</span>
            <Badge tone={requestStatus.tone}>{requestStatus.label}</Badge>
          </p>
        </Card>

        {editable ? (
          // Resets the form when another project is selected.
          <VariablesForm key={project.id} snapshot={snapshot} project={project} onUpdated={onUpdated} onNavigate={onNavigate} />
        ) : (
          <>
            <Alert tone="neutral" title="Variables verrouillées">
              La demande d'accès de ce projet a été soumise à l'Autorité de gouvernance : ses variables sont examinées
              telles qu'elles ont été demandées et ne peuvent plus être modifiées. L'autorisation peut n'en retenir
              qu'une partie.
            </Alert>
            <Card title="Variables soumises">
              {entries.length > 0 ? (
                <VariableList variables={entries} />
              ) : (
                unmatched.length === 0 && <p className="text-slate-700">Aucune variable demandée.</p>
              )}
              {unmatched.length > 0 && (
                <p className="mt-2 text-sm text-slate-600">Hors catalogue : {unmatched.join(', ')}.</p>
              )}
              <div className="mt-4 border-t border-slate-200 pt-4">
                <h2 className="mb-2 font-semibold text-slate-900">Justification</h2>
                <p className="text-sm text-slate-700">
                  {project.variablesJustification ??
                    'Justification non structurée : ce projet de démonstration la porte dans son protocole.'}
                </p>
              </div>
            </Card>
          </>
        )}
      </div>
    </>
  )
}

function VariablesForm({
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
  const [draft, setDraft] = useState<VariablesDraft>(() => draftFromProject(project))
  // Errors are shown once the researcher has tried to save.
  const [showErrors, setShowErrors] = useState(false)
  const [saving, setSaving] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const allErrors = validateVariablesDraft(draft)
  const errors = showErrors ? allErrors : {}
  const selected = catalogEntries(draft.names)
  const quasiIdentifiers = selected.filter((v) => v.quasiIdentifier).length

  const toggle = (name: string, checked: boolean) => {
    setDraft((d) => ({ ...d, names: checked ? [...d.names, name] : d.names.filter((n) => n !== name) }))
    setSaved(false)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setShowErrors(true)
    setFailure(null)
    if (Object.keys(allErrors).length > 0) return
    setSaving(true)
    try {
      onUpdated(await saveVariables(snapshot, project.id, draft))
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
          title="Variables enregistrées"
          actions={<Button onClick={() => onNavigate('hospitals')}>Continuer : établissements</Button>}
        >
          Demander des variables ne donne accès à aucune donnée : elles seront examinées avec la demande d'accès
          (HC-097).
        </Alert>
      )}
      {failure && (
        <Alert tone="danger" title="Les variables n'ont pas été enregistrées">
          {failure}
        </Alert>
      )}

      <Card title="Sélection des variables">
        <form noValidate onSubmit={submit} className="space-y-5">
          <p className="text-sm text-slate-600">
            Ne demandez que les variables nécessaires à l'objectif du projet ({MAX_VARIABLES} au plus). Le catalogue ne
            propose que des données dérivées ou regroupées : nom, date de naissance, adresse et numéro de dossier ne
            peuvent pas être demandés.
          </p>

          {CATEGORIES.map((category) => (
            <fieldset key={category} className="space-y-3">
              <legend className="font-medium text-slate-800">{CATEGORY_LABELS[category]}</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {VARIABLE_CATALOG.filter((v) => v.category === category).map((v) => (
                  <CheckboxField
                    key={v.name}
                    label={v.label}
                    hint={`${v.description}${v.quasiIdentifier ? ' Quasi-identifiant.' : ''}`}
                    checked={draft.names.includes(v.name)}
                    onChange={(e) => toggle(v.name, e.target.checked)}
                    disabled={saving}
                  />
                ))}
              </div>
            </fieldset>
          ))}

          {errors.names && (
            <p role="alert" className="text-sm font-medium text-danger-700">
              {errors.names}
            </p>
          )}

          <TextareaField
            label="Justification"
            required
            rows={3}
            maxLength={JUSTIFICATION_MAX}
            value={draft.justification}
            onChange={(e) => {
              const justification = e.target.value
              setDraft((d) => ({ ...d, justification }))
              setSaved(false)
            }}
            error={errors.justification}
            hint={`Pourquoi chaque variable est nécessaire à l'objectif, tel que l'Autorité de gouvernance le lira (${draft.justification.trim().length}/${JUSTIFICATION_MAX}).`}
            disabled={saving}
          />

          <div className="rounded-xl bg-slate-50 p-4">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">
              Variables demandées à chaque Hospital Node ({selected.length}/{MAX_VARIABLES})
            </h2>
            {selected.length > 0 ? (
              <VariableList variables={selected} />
            ) : (
              <p className="text-sm text-slate-500">Aucune variable pour l'instant.</p>
            )}
            {quasiIdentifiers >= 2 && (
              <p className="mt-2 text-xs text-warning-700">
                {quasiIdentifiers} quasi-identifiants combinés : les résultats agrégés seront plus souvent masqués par le
                contrôle de taille minimale des cellules.
              </p>
            )}
          </div>

          <Button type="submit" loading={saving}>
            Enregistrer les variables
          </Button>
        </form>
      </Card>
    </>
  )
}
