import { useState, type FormEvent, type ReactNode } from 'react'
import {
  Alert,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  TextareaField,
  TextField,
} from '@hackcure/design-system'
import {
  applyTechnical,
  canEditTechnical,
  demoTechnicalInput,
  HOSTING_LABELS,
  QUESTION_LABELS,
  RESOURCE_FIELDS,
  saveTechnical,
  technicalInputFrom,
  validateTechnical,
  YES_NO_FIELDS,
  type TechnicalErrors,
  type TechnicalField,
  type TechnicalInput,
} from '../services/technicalService'
import type { HostingType, OnboardingSnapshot, StepId, TechnicalQuestionnaire } from '../types/onboarding'

interface TechnicalViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make this save fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

const hostingOptions = (Object.keys(HOSTING_LABELS) as HostingType[]).map((value) => ({
  value,
  label: HOSTING_LABELS[value],
}))
const yesNoOptions = [
  { value: 'yes', label: 'Oui' },
  { value: 'no', label: 'Non' },
]

export function TechnicalView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: TechnicalViewProps) {
  const { application, manager } = snapshot
  const editable = canEditTechnical(application)
  const questionnaire = application?.technicalQuestionnaire ?? null
  const [editing, setEditing] = useState(editable && !questionnaire)
  const [justSaved, setJustSaved] = useState(false)

  const header = (
    <PageHeader
      eyebrow="Étape 5 · Parcours d'adhésion"
      title="Questionnaire technique"
      description="Environnement de déploiement prévu pour votre futur Hospital Node : hébergement, ressources, réseau et exploitation."
      actions={<DemoBadge>Questionnaire simulé</DemoBadge>}
    />
  )

  if (!application) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune inscription"
            description="Inscrivez d'abord votre établissement pour décrire son environnement technique."
            action={<Button onClick={() => onNavigate('registration')}>Aller à l'inscription</Button>}
          />
        </Card>
      </>
    )
  }

  const contactName =
    questionnaire && questionnaire.technicalContactId !== manager.id
      ? questionnaire.technicalContactId
      : `${manager.firstName} ${manager.lastName}`

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="info" title="Informations déclaratives">
          Vos réponses décrivent l'environnement prévu ; elles n'installent rien et ne valent pas validation technique.
          Le Hospital Node reste sous le contrôle de votre établissement.
        </Alert>
        {justSaved && !editing && (
          <Alert
            tone="success"
            title="Questionnaire enregistré (simulation)"
            actions={<Button onClick={() => onNavigate('dmi')}>Continuer : questionnaire DMI / SIH</Button>}
          >
            Les réponses sont conservées dans cette page jusqu'à son rechargement.
          </Alert>
        )}
        {!editable && (
          <Alert tone="neutral" title="Questionnaire verrouillé">
            Votre candidature a été transmise pour revue : le questionnaire ne peut plus être modifié depuis le portail.
          </Alert>
        )}

        {editing ? (
          <TechnicalForm
            snapshot={snapshot}
            contactName={contactName}
            consumeSimulatedFailure={consumeSimulatedFailure}
            onCancel={questionnaire ? () => setEditing(false) : undefined}
            onSaved={(next) => {
              onUpdated(next)
              setEditing(false)
              setJustSaved(true)
            }}
          />
        ) : questionnaire ? (
          <TechnicalSummary
            questionnaire={questionnaire}
            contactName={contactName}
            onEdit={
              editable
                ? () => {
                    setJustSaved(false)
                    setEditing(true)
                  }
                : undefined
            }
          />
        ) : (
          <Card>
            <EmptyState
              title="Questionnaire non disponible"
              description="Cette candidature a été instruite avant l'introduction du questionnaire technique."
            />
          </Card>
        )}
      </div>
    </>
  )
}

function Details({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[16rem_1fr]">
      {rows.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-slate-500">{term}</dt>
          <dd className="font-medium break-words text-slate-900">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function TechnicalSummary({
  questionnaire: q,
  contactName,
  onEdit,
}: {
  questionnaire: TechnicalQuestionnaire
  contactName: string
  onEdit?: () => void
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card
        title="Hébergement et ressources"
        actions={
          onEdit && (
            <Button variant="secondary" size="sm" onClick={onEdit}>
              Modifier
            </Button>
          )
        }
      >
        <Details
          rows={[
            ['Hébergement', HOSTING_LABELS[q.hostingType]],
            ["Système d'exploitation", q.operatingSystem],
            [RESOURCE_FIELDS.cpuCores.label, `${q.cpuCores} ${RESOURCE_FIELDS.cpuCores.unit}`],
            [RESOURCE_FIELDS.memoryGb.label, `${q.memoryGb} ${RESOURCE_FIELDS.memoryGb.unit}`],
            [RESOURCE_FIELDS.storageGb.label, `${q.storageGb} ${RESOURCE_FIELDS.storageGb.unit}`],
          ]}
        />
      </Card>
      <Card title="Réseau et exploitation">
        <Details
          rows={[
            [RESOURCE_FIELDS.bandwidthMbps.label, `${q.bandwidthMbps} ${RESOURCE_FIELDS.bandwidthMbps.unit}`],
            ['Réseau', q.network],
            ...YES_NO_FIELDS.map((field): [string, string] => [QUESTION_LABELS[field], q[field] ? 'Oui' : 'Non']),
            ['Contact technique', contactName],
          ]}
        />
      </Card>
    </div>
  )
}

type Save = { kind: 'idle' } | { kind: 'saving' } | { kind: 'failed'; message: string }

function TechnicalForm({
  snapshot,
  contactName,
  consumeSimulatedFailure,
  onCancel,
  onSaved,
}: {
  snapshot: OnboardingSnapshot
  contactName: string
  consumeSimulatedFailure: () => boolean
  onCancel?: () => void
  onSaved: (snapshot: OnboardingSnapshot) => void
}) {
  const [input, setInput] = useState<TechnicalInput>(() => technicalInputFrom(snapshot.application))
  const [errors, setErrors] = useState<TechnicalErrors>({})
  const [save, setSave] = useState<Save>({ kind: 'idle' })
  const saving = save.kind === 'saving'

  const field = (name: TechnicalField) => ({
    value: input[name],
    error: errors[name],
    disabled: saving,
    required: true,
    onChange: (e: { target: { value: string } }) => {
      setInput((current) => ({ ...current, [name]: e.target.value }))
      setErrors((current) => ({ ...current, [name]: undefined }))
    },
  })

  const submit = async () => {
    const found = validateTechnical(input)
    setErrors(found)
    if (Object.keys(found).length > 0) return
    setSave({ kind: 'saving' })
    try {
      const result = await saveTechnical(
        input,
        snapshot.manager.id,
        snapshot.application?.technicalQuestionnaire ?? null,
        { simulateFailure: consumeSimulatedFailure() },
      )
      if (result.kind === 'rejected') {
        setErrors(result.errors)
        setSave({ kind: 'idle' })
        return
      }
      onSaved(applyTechnical(snapshot, result.questionnaire))
    } catch (error) {
      setSave({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    void submit()
  }

  const errorCount = Object.values(errors).filter(Boolean).length

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {save.kind === 'failed' && (
        <Alert
          tone="danger"
          title="Questionnaire non enregistré"
          actions={<Button variant="secondary" onClick={() => void submit()}>Réessayer</Button>}
        >
          {save.message} Vos réponses sont conservées.
        </Alert>
      )}
      {errorCount > 0 && (
        <Alert tone="warning" title="Questionnaire incomplet">
          {errorCount} réponse{errorCount > 1 ? 's' : ''} à corriger.
        </Alert>
      )}

      <Card
        title="Hébergement et ressources"
        actions={
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={saving}
            onClick={() => {
              setInput(demoTechnicalInput())
              setErrors({})
            }}
          >
            Remplir avec l'exemple fictif
          </Button>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField label="Type d'hébergement" placeholder="Choisir…" options={hostingOptions} {...field('hostingType')} />
          <TextField label="Système d'exploitation" hint="Distribution et version." {...field('operatingSystem')} />
          {(['cpuCores', 'memoryGb', 'storageGb'] as const).map((name) => (
            <TextField
              key={name}
              label={`${RESOURCE_FIELDS[name].label} (${RESOURCE_FIELDS[name].unit})`}
              inputMode="numeric"
              {...field(name)}
            />
          ))}
        </div>
      </Card>

      <Card
        title="Réseau et exploitation"
        footer={
          <div className="flex flex-wrap justify-end gap-2">
            {onCancel && (
              <Button type="button" variant="secondary" disabled={saving} onClick={onCancel}>
                Annuler
              </Button>
            )}
            <Button type="submit" loading={saving}>
              Enregistrer le questionnaire
            </Button>
          </div>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label={`${RESOURCE_FIELDS.bandwidthMbps.label} (${RESOURCE_FIELDS.bandwidthMbps.unit})`}
            inputMode="numeric"
            {...field('bandwidthMbps')}
          />
          <TextField label="Contact technique" value={contactName} hint="Le responsable inscrit." readOnly disabled />
          <TextareaField
            label="Description du réseau"
            hint="Type de lien, segmentation, pare-feu."
            className="sm:col-span-2"
            rows={3}
            {...field('network')}
          />
          {YES_NO_FIELDS.map((name) => (
            <SelectField
              key={name}
              label={QUESTION_LABELS[name]}
              placeholder="Choisir…"
              options={yesNoOptions}
              {...field(name)}
            />
          ))}
        </div>
      </Card>
    </form>
  )
}
