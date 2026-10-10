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
  type Tone,
} from '@hackcure/design-system'
import { requestStatusDisplay } from '../presentation'
import { defaultDraftId, isEditableDraft } from '../services/projectCreation'
import {
  draftFromProject,
  hospitalEligibility,
  hospitalsStatus,
  isSelectable,
  saveHospitals,
  selectedHospitals,
  validateHospitalsDraft,
  type HospitalEligibility,
  type HospitalsDraft,
  type HospitalsStatus,
} from '../services/projectHospitals'
import { HEALTHCARE_ORGANIZATIONS } from '../services/researchService'
import type { Organization, PageId, ResearchProject, ResearchSnapshot } from '../types/research'

interface HospitalsViewProps {
  snapshot: ResearchSnapshot
  onUpdated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}

const statusDisplay: Record<HospitalsStatus, { label: string; tone: Tone }> = {
  selected: { label: 'Sélectionnés', tone: 'success' },
  missing: { label: 'À sélectionner', tone: 'warning' },
}

const eligibilityDisplay: Record<HospitalEligibility, { label: string; tone: Tone; hint: string }> = {
  eligible: { label: 'Nœud en ligne', tone: 'success', hint: 'Hospital Node approuvé et en ligne.' },
  degraded: {
    label: 'Nœud dégradé',
    tone: 'warning',
    hint: "Hospital Node approuvé mais dégradé ou DMI déconnecté : l'exécution pourra y échouer.",
  },
  not_federated: {
    label: 'Non fédéré',
    tone: 'neutral',
    hint: "Adhésion pas encore approuvée par la gouvernance, aucun Hospital Node : il ne peut pas être sollicité.",
  },
}

const typeLabels: Record<string, string> = {
  hospital: 'Hôpital',
  private_practice: 'Cabinet médical',
}

function EligibilityBadge({ organization }: { organization: Organization }) {
  const display = eligibilityDisplay[hospitalEligibility(organization)]
  return <Badge tone={display.tone}>{display.label}</Badge>
}

function HospitalList({ organizations }: { organizations: Organization[] }) {
  return (
    <ul className="space-y-2">
      {organizations.map((o) => (
        <li key={o.id} className="flex flex-wrap items-center gap-2 text-slate-800">
          <span className="font-medium">{o.name}</span>
          <span className="text-sm text-slate-500">{o.city}</span>
          {o.node && <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{o.node.id}</code>}
          <EligibilityBadge organization={o} />
        </li>
      ))}
    </ul>
  )
}

/** Participating hospitals selection (HC-096): MOCKED directory, saved on the draft in session state. */
export function HospitalsView({ snapshot, onUpdated, onNavigate }: HospitalsViewProps) {
  const [selectedId, setSelectedId] = useState(() => defaultDraftId(snapshot))

  const header = (
    <PageHeader
      eyebrow="Projets et demandes · HC-096"
      title="Établissements participants"
      description="Les établissements dont le Hospital Node exécuterait l'analyse, examinés par l'Autorité de gouvernance et d'éthique avec la demande d'accès."
      actions={<DemoBadge>Annuaire fictif</DemoBadge>}
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
            description="Créez d'abord un projet pour choisir ses établissements participants."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  const { project, request } = summary
  const editable = isEditableDraft(summary)
  const status = statusDisplay[hospitalsStatus(project)]
  const requestStatus = requestStatusDisplay[request?.status ?? 'not_submitted']

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Aucun établissement n'est contacté">
          Sélectionner un établissement ne lui transmet rien et ne donne accès à aucune donnée : après autorisation,
          le code d'analyse s'exécute dans chaque Hospital Node autorisé, qui vérifie lui-même l'autorisation, et seuls
          des résultats agrégés contrôlés reviennent. L'annuaire et l'état des nœuds sont fictifs. L'enregistrement est
          conservé dans cette page jusqu'à son rechargement.
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
            <span>Établissements :</span>
            <Badge tone={status.tone}>{status.label}</Badge>
            <span>Demande d'accès :</span>
            <Badge tone={requestStatus.tone}>{requestStatus.label}</Badge>
          </p>
        </Card>

        {editable ? (
          // Resets the form when another project is selected.
          <HospitalsForm key={project.id} snapshot={snapshot} project={project} onUpdated={onUpdated} onNavigate={onNavigate} />
        ) : (
          <>
            <Alert tone="neutral" title="Établissements verrouillés">
              La demande d'accès de ce projet a été soumise à l'Autorité de gouvernance : ses établissements sont
              examinés tels qu'ils ont été demandés et ne peuvent plus être modifiés. L'autorisation peut n'en retenir
              qu'une partie.
            </Alert>
            <Card title="Établissements soumis">
              {summary.participatingOrganizations.length > 0 ? (
                <HospitalList organizations={summary.participatingOrganizations} />
              ) : (
                <p className="text-slate-700">Aucun établissement demandé.</p>
              )}
            </Card>
          </>
        )}
      </div>
    </>
  )
}

function HospitalsForm({
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
  const [draft, setDraft] = useState<HospitalsDraft>(() => draftFromProject(project))
  // Errors are shown once the researcher has tried to save.
  const [showErrors, setShowErrors] = useState(false)
  const [saving, setSaving] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const allErrors = validateHospitalsDraft(draft)
  const errors = showErrors ? allErrors : {}
  const selected = selectedHospitals(draft.organizationIds)
  const degraded = selected.filter((o) => hospitalEligibility(o) === 'degraded').length

  const toggle = (id: string, checked: boolean) => {
    setDraft((d) => ({
      organizationIds: checked ? [...d.organizationIds, id] : d.organizationIds.filter((n) => n !== id),
    }))
    setSaved(false)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setShowErrors(true)
    setFailure(null)
    if (Object.keys(allErrors).length > 0) return
    setSaving(true)
    try {
      onUpdated(await saveHospitals(snapshot, project.id, draft))
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
          title="Établissements enregistrés"
          actions={<Button onClick={() => onNavigate('submit-request')}>Continuer : demande d'accès</Button>}
        >
          Aucun établissement n'a été contacté : la sélection sera examinée avec la demande d'accès (HC-097).
        </Alert>
      )}
      {failure && (
        <Alert tone="danger" title="Les établissements n'ont pas été enregistrés">
          {failure}
        </Alert>
      )}

      <Card title="Sélection des établissements">
        <form noValidate onSubmit={submit} className="space-y-5">
          <p className="text-sm text-slate-600">
            Seuls les établissements dont l'adhésion est approuvée par l'Autorité de gouvernance disposent d'un Hospital
            Node et peuvent être sollicités. Chaque établissement garde ses données : aucune n'est centralisée.
          </p>

          <fieldset className="space-y-3">
            <legend className="font-medium text-slate-800">Écosystème fédéré</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {HEALTHCARE_ORGANIZATIONS.map((o) => (
                <div key={o.id} className="space-y-2 rounded-md border border-slate-200 p-3">
                  <CheckboxField
                    label={o.name}
                    hint={`${typeLabels[o.type] ?? o.type} · ${o.city}. ${eligibilityDisplay[hospitalEligibility(o)].hint}`}
                    checked={draft.organizationIds.includes(o.id)}
                    onChange={(e) => toggle(o.id, e.target.checked)}
                    disabled={saving || !isSelectable(o)}
                  />
                  <div className="pl-7">
                    <EligibilityBadge organization={o} />
                  </div>
                </div>
              ))}
            </div>
          </fieldset>

          {errors.organizationIds && (
            <p role="alert" className="text-sm font-medium text-danger-700">
              {errors.organizationIds}
            </p>
          )}

          <div className="rounded-md bg-slate-50 p-4">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">
              Hospital Nodes sollicités après autorisation ({selected.length})
            </h2>
            {selected.length > 0 ? (
              <HospitalList organizations={selected} />
            ) : (
              <p className="text-sm text-slate-500">Aucun établissement pour l'instant.</p>
            )}
            {degraded > 0 && (
              <p className="mt-2 text-xs text-warning-700">
                {degraded} nœud(s) dégradé(s) : l'exécution pourra y échouer tant qu'ils ne sont pas rétablis.
              </p>
            )}
          </div>

          <Button type="submit" loading={saving}>
            Enregistrer les établissements
          </Button>
        </form>
      </Card>
    </>
  )
}
