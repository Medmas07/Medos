import { useState, type FormEvent, type ReactNode } from 'react'
import {
  Alert,
  Button,
  Card,
  CheckboxField,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  TextareaField,
  TextField,
} from '@hackcure/design-system'
import {
  applyDmi,
  canEditDmi,
  demoDmiInput,
  DMI_HOSTING_LABELS,
  dmiInputFrom,
  hasDmiAnswers,
  hasTechnicalQuestionnaire,
  INTEGRATION_LABELS,
  NOTES_MAX_LENGTH,
  saveDmi,
  toggleMethod,
  validateDmi,
  type DmiErrors,
  type DmiInput,
} from '../services/dmiService'
import type { DmiHosting, IntegrationMethod, OnboardingSnapshot, StepId, TechnicalQuestionnaire } from '../types/onboarding'

interface DmiViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make this save fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

const hostingOptions = (Object.keys(DMI_HOSTING_LABELS) as DmiHosting[]).map((value) => ({
  value,
  label: DMI_HOSTING_LABELS[value],
}))
const methods = Object.keys(INTEGRATION_LABELS) as IntegrationMethod[]

export function DmiView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: DmiViewProps) {
  const { application } = snapshot
  const questionnaire = application?.technicalQuestionnaire ?? null
  const editable = canEditDmi(application)
  const answered = hasDmiAnswers(questionnaire)
  const [editing, setEditing] = useState(editable && !answered)
  const [justSaved, setJustSaved] = useState(false)

  const header = (
    <PageHeader
      eyebrow="Étape 6 · Parcours d'adhésion"
      title="Questionnaire DMI / SIH"
      description="Votre dossier médical informatisé existant et les moyens d'en extraire les données, pour préparer l'adaptateur DMI de votre Hospital Node."
      actions={<DemoBadge>Questionnaire simulé</DemoBadge>}
    />
  )

  const boundary = (
    <Alert tone="info" title="Votre DMI reste chez vous">
      Ces informations préparent l'adaptateur DMI qui fonctionnera <strong>dans votre Hospital Node</strong>, sous le
      contrôle de votre établissement. Aucun service central ne se connecte à votre DMI. Ne saisissez ni identifiant,
      ni mot de passe, ni adresse réseau interne, ni donnée patient.
    </Alert>
  )

  if (!application || !hasTechnicalQuestionnaire(application)) {
    return (
      <>
        {header}
        <div className="space-y-6">
          {boundary}
          <Card>
            {application ? (
              <EmptyState
                title="Questionnaire technique requis"
                description="Décrivez d'abord l'environnement de déploiement : les informations DMI le complètent."
                action={<Button onClick={() => onNavigate('technical')}>Aller au questionnaire technique</Button>}
              />
            ) : (
              <EmptyState
                title="Aucune inscription"
                description="Inscrivez d'abord votre établissement pour décrire son DMI / SIH."
                action={<Button onClick={() => onNavigate('registration')}>Aller à l'inscription</Button>}
              />
            )}
          </Card>
        </div>
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        {boundary}
        {justSaved && !editing && (
          <Alert
            tone="success"
            title="Informations DMI enregistrées (simulation)"
            actions={<Button onClick={() => onNavigate('automated-review')}>Continuer : revue automatisée</Button>}
          >
            Les réponses sont conservées dans cette page jusqu'à son rechargement.
          </Alert>
        )}
        {application.status !== 'draft' && (
          <Alert tone="neutral" title="Questionnaire verrouillé">
            Votre candidature a été transmise pour revue : ces informations ne peuvent plus être modifiées depuis le
            portail.
          </Alert>
        )}

        {editing ? (
          <DmiForm
            snapshot={snapshot}
            questionnaire={questionnaire!}
            consumeSimulatedFailure={consumeSimulatedFailure}
            onCancel={answered ? () => setEditing(false) : undefined}
            onSaved={(next) => {
              onUpdated(next)
              setEditing(false)
              setJustSaved(true)
            }}
          />
        ) : answered ? (
          <DmiSummary
            questionnaire={questionnaire!}
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
            <EmptyState title="Informations DMI non renseignées" description="Ce dossier ne décrit pas son DMI / SIH." />
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

function DmiSummary({ questionnaire: q, onEdit }: { questionnaire: TechnicalQuestionnaire; onEdit?: () => void }) {
  const methodList = (q.integrationMethods ?? []).map((m) => INTEGRATION_LABELS[m].label).join(', ')
  return (
    <Card
      title="DMI / SIH déclaré"
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
          ['DMI / SIH', q.dmiSystem],
          ['Base de données', q.database],
          ['Hébergement du DMI', q.dmiHosting ? DMI_HOSTING_LABELS[q.dmiHosting] : 'Non renseigné'],
          ["Méthodes d'intégration", methodList],
          ['Environnement de test', q.testEnvironmentAvailable ? 'Disponible' : 'Non disponible'],
          ['Contraintes connues', q.dmiNotes ?? 'Aucune'],
        ]}
      />
    </Card>
  )
}

type Save = { kind: 'idle' } | { kind: 'saving' } | { kind: 'failed'; message: string }

function DmiForm({
  snapshot,
  questionnaire,
  consumeSimulatedFailure,
  onCancel,
  onSaved,
}: {
  snapshot: OnboardingSnapshot
  questionnaire: TechnicalQuestionnaire
  consumeSimulatedFailure: () => boolean
  onCancel?: () => void
  onSaved: (snapshot: OnboardingSnapshot) => void
}) {
  const [input, setInput] = useState<DmiInput>(() => dmiInputFrom(questionnaire))
  const [errors, setErrors] = useState<DmiErrors>({})
  const [save, setSave] = useState<Save>({ kind: 'idle' })
  const saving = save.kind === 'saving'

  const set = <K extends keyof DmiInput>(name: K, value: DmiInput[K]) => {
    setInput((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }
  const text = (name: 'dmiSystem' | 'database' | 'dmiHosting' | 'testEnvironmentAvailable') => ({
    value: input[name],
    error: errors[name],
    disabled: saving,
    required: true,
    onChange: (e: { target: { value: string } }) => set(name, e.target.value as never),
  })

  const submit = async () => {
    const found = validateDmi(input)
    setErrors(found)
    if (Object.keys(found).length > 0) return
    setSave({ kind: 'saving' })
    try {
      const result = await saveDmi(questionnaire, input, { simulateFailure: consumeSimulatedFailure() })
      if (result.kind === 'rejected') {
        setErrors(result.errors)
        setSave({ kind: 'idle' })
        return
      }
      onSaved(applyDmi(snapshot, result.questionnaire))
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
          title="Informations DMI non enregistrées"
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
        title="Système existant"
        actions={
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={saving}
            onClick={() => {
              setInput(demoDmiInput())
              setErrors({})
            }}
          >
            Remplir avec l'exemple fictif
          </Button>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="DMI / SIH (produit et version)" {...text('dmiSystem')} />
          <TextField label="Base de données du DMI (moteur et version)" {...text('database')} />
          <SelectField label="Hébergement du DMI" placeholder="Choisir…" options={hostingOptions} {...text('dmiHosting')} />
          <SelectField
            label="Environnement de test du DMI disponible"
            placeholder="Choisir…"
            options={[
              { value: 'yes', label: 'Oui' },
              { value: 'no', label: 'Non' },
            ]}
            {...text('testEnvironmentAvailable')}
          />
        </div>
      </Card>

      <Card
        title="Méthodes d'intégration disponibles"
        description="Comment l'adaptateur DMI local pourra lire les données. Plusieurs réponses possibles."
        footer={
          <div className="flex flex-wrap justify-end gap-2">
            {onCancel && (
              <Button type="button" variant="secondary" disabled={saving} onClick={onCancel}>
                Annuler
              </Button>
            )}
            <Button type="submit" loading={saving}>
              Enregistrer les informations DMI
            </Button>
          </div>
        }
      >
        <fieldset className="space-y-3" aria-describedby={errors.integrationMethods ? 'integration-error' : undefined}>
          <legend className="sr-only">Méthodes d'intégration</legend>
          {methods.map((method) => (
            <CheckboxField
              key={method}
              label={INTEGRATION_LABELS[method].label}
              hint={INTEGRATION_LABELS[method].hint}
              checked={input.integrationMethods.includes(method)}
              disabled={saving}
              onChange={(e) => set('integrationMethods', toggleMethod(input.integrationMethods, method, e.target.checked))}
            />
          ))}
          {errors.integrationMethods && (
            <p id="integration-error" className="text-xs font-medium text-danger-700">
              {errors.integrationMethods}
            </p>
          )}
        </fieldset>
        <div className="mt-6">
          <TextareaField
            label="Contraintes connues (facultatif)"
            hint={`Fenêtres d'export, limites de l'éditeur… ${NOTES_MAX_LENGTH} caractères au maximum, sans donnée sensible.`}
            rows={3}
            value={input.dmiNotes}
            error={errors.dmiNotes}
            disabled={saving}
            onChange={(e) => set('dmiNotes', e.target.value)}
          />
        </div>
      </Card>
    </form>
  )
}
