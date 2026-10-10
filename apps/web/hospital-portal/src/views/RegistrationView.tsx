import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CheckboxField,
  DemoBadge,
  PageHeader,
  SelectField,
  TextField,
} from '@hackcure/design-system'
import { applicationStatusDisplay, formatDateTime } from '../presentation'
import {
  applyRegistration,
  demoRegistrationInput,
  EMPTY_REGISTRATION,
  firstStepWithError,
  ORGANIZATION_TYPE_LABELS,
  REGISTRATION_STEPS,
  submitRegistration,
  validateRegistration,
  type OrganizationType,
  type RegistrationErrors,
  type RegistrationField,
  type RegistrationInput,
} from '../services/registrationService'
import type { OnboardingSnapshot, StepId } from '../types/onboarding'

interface RegistrationViewProps {
  snapshot: OnboardingSnapshot
  /** First submission fails, to demonstrate the error state. */
  failFirstSubmission: boolean
  onRegistered: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

const typeOptions = (Object.keys(ORGANIZATION_TYPE_LABELS) as OrganizationType[]).map((value) => ({
  value,
  label: ORGANIZATION_TYPE_LABELS[value],
}))

const GOVERNANCE_NOTICE =
  "L'inscription crée le dossier de votre établissement. Elle ne vaut pas approbation : seule l'Autorité de gouvernance et d'éthique décide de l'adhésion, après les vérifications et la revue humaine."

export function RegistrationView({ snapshot, failFirstSubmission, onRegistered, onNavigate }: RegistrationViewProps) {
  return (
    <>
      <PageHeader
        eyebrow="Étape 1 · Parcours d'adhésion"
        title="Inscription de l'établissement"
        description="Créez le dossier de votre établissement et désignez son responsable pour lancer le parcours d'adhésion."
        actions={<DemoBadge>Inscription simulée</DemoBadge>}
      />
      {snapshot.application ? (
        <RegistrationSummary snapshot={snapshot} onNavigate={onNavigate} />
      ) : (
        <RegistrationForm snapshot={snapshot} failFirstSubmission={failFirstSubmission} onRegistered={onRegistered} />
      )}
    </>
  )
}

function RegistrationSummary({
  snapshot,
  onNavigate,
}: Pick<RegistrationViewProps, 'snapshot' | 'onNavigate'>) {
  const { organization, manager } = snapshot
  const application = snapshot.application!
  const status = applicationStatusDisplay[application.status]
  const justRegistered = application.status === 'draft'
  const typeLabel = ORGANIZATION_TYPE_LABELS[organization.type as OrganizationType] ?? organization.type

  const rows: [string, string][] = [
    ['Établissement', organization.name],
    ['Nom court', organization.shortName],
    ['Type', typeLabel],
    ['Ville', organization.city],
    ['Responsable', `${manager.firstName} ${manager.lastName}`],
    ...(manager.email ? ([['E-mail', manager.email]] as [string, string][]) : []),
    ...(manager.phone ? ([['Téléphone', manager.phone]] as [string, string][]) : []),
    ['Référence', application.id],
    ['Enregistrée le', formatDateTime(application.submittedAt)],
  ]

  return (
    <div className="space-y-6">
      <Alert
        tone="success"
        title={justRegistered ? 'Inscription enregistrée (simulation)' : 'Votre établissement est inscrit'}
        actions={
          justRegistered && (
            <Button onClick={() => onNavigate('profile')}>Continuer : profil de l'établissement</Button>
          )
        }
      >
        {justRegistered
          ? `Référence ${application.id}. Aucun compte réel n'a été créé ; l'inscription est conservée dans cette page jusqu'à son rechargement.`
          : 'Votre dossier a déjà été transmis. Suivez son avancement depuis le tableau de bord.'}
      </Alert>
      <Card title="Récapitulatif de l'inscription" actions={<Badge tone={status.tone}>{status.label}</Badge>}>
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[12rem_1fr]">
          {rows.map(([term, value]) => (
            <div key={term} className="contents">
              <dt className="text-slate-500">{term}</dt>
              <dd className="font-medium break-words text-slate-900">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>
      <Alert tone="info" title="Prochaine décision : Autorité de gouvernance">
        {GOVERNANCE_NOTICE}
      </Alert>
    </div>
  )
}

type Submission = { kind: 'idle' } | { kind: 'submitting' } | { kind: 'failed'; message: string }

function RegistrationForm({
  snapshot,
  failFirstSubmission,
  onRegistered,
}: Pick<RegistrationViewProps, 'snapshot' | 'failFirstSubmission' | 'onRegistered'>) {
  const [input, setInput] = useState<RegistrationInput>(EMPTY_REGISTRATION)
  const [errors, setErrors] = useState<RegistrationErrors>({})
  const [stepIndex, setStepIndex] = useState(0)
  const [submission, setSubmission] = useState<Submission>({ kind: 'idle' })
  const [attempts, setAttempts] = useState(0)

  const step = REGISTRATION_STEPS[stepIndex]
  const isLast = stepIndex === REGISTRATION_STEPS.length - 1
  const submitting = submission.kind === 'submitting'

  const update = <K extends RegistrationField>(field: K, value: RegistrationInput[K]) => {
    setInput((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  const text = (field: RegistrationField) => ({
    value: input[field] as string,
    error: errors[field],
    disabled: submitting,
    required: true,
    onChange: (e: { target: { value: string } }) => update(field, e.target.value as never),
  })

  const submit = async () => {
    const all = validateRegistration(input)
    if (Object.keys(all).length > 0) {
      setErrors(all)
      setStepIndex(firstStepWithError(all))
      return
    }
    const attempt = attempts + 1
    setAttempts(attempt)
    setSubmission({ kind: 'submitting' })
    try {
      const result = await submitRegistration(input, { simulateFailure: failFirstSubmission && attempt === 1 })
      if (result.kind === 'rejected') {
        setErrors(result.errors)
        setStepIndex(Math.max(0, firstStepWithError(result.errors)))
        setSubmission({ kind: 'idle' })
        return
      }
      onRegistered(applyRegistration(snapshot, input, result.receipt))
    } catch (error) {
      setSubmission({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!isLast) {
      const stepErrors = validateRegistration(input, step.fields)
      setErrors(stepErrors)
      if (Object.keys(stepErrors).length === 0) setStepIndex(stepIndex + 1)
      return
    }
    void submit()
  }

  return (
    <div className="space-y-6">
      <Alert tone="info" title="L'inscription ne vaut pas approbation">
        {GOVERNANCE_NOTICE}
      </Alert>

      <ol aria-label="Étapes de l'inscription" className="flex flex-wrap gap-2">
        {REGISTRATION_STEPS.map((s, index) => (
          <li key={s.id}>
            <Badge tone={index < stepIndex ? 'success' : index === stepIndex ? 'info' : 'neutral'}>
              {index + 1}. {s.label}
            </Badge>
          </li>
        ))}
      </ol>

      {submission.kind === 'failed' && (
        <Alert
          tone="danger"
          title="Inscription non envoyée"
          actions={<Button variant="secondary" onClick={() => void submit()}>Réessayer</Button>}
        >
          {submission.message} Vos informations sont conservées.
        </Alert>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <Card
          title={`Étape ${stepIndex + 1} sur ${REGISTRATION_STEPS.length} : ${step.label}`}
          actions={
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={submitting}
              onClick={() => {
                setInput(demoRegistrationInput())
                setErrors({})
              }}
            >
              Remplir avec l'exemple fictif
            </Button>
          }
          footer={
            <div className="flex flex-wrap justify-between gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={stepIndex === 0 || submitting}
                onClick={() => setStepIndex(stepIndex - 1)}
              >
                Précédent
              </Button>
              <Button type="submit" loading={submitting}>
                {isLast ? "Envoyer l'inscription" : 'Suivant'}
              </Button>
            </div>
          }
        >
          {step.id === 'organization' && (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField
                label="Nom officiel de l'établissement"
                className="sm:col-span-2"
                autoComplete="organization"
                {...text('organizationName')}
              />
              <TextField label="Nom court" hint="Affiché dans l'écosystème." {...text('shortName')} />
              <SelectField
                label="Type d'établissement"
                placeholder="Choisir…"
                options={typeOptions}
                {...text('organizationType')}
              />
              <TextField label="Ville" autoComplete="address-level2" {...text('city')} />
            </div>
          )}

          {step.id === 'manager' && (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField label="Prénom" autoComplete="given-name" {...text('managerFirstName')} />
              <TextField label="Nom" autoComplete="family-name" {...text('managerLastName')} />
              <TextField
                label="E-mail professionnel"
                type="email"
                autoComplete="email"
                {...text('managerEmail')}
              />
              <TextField label="Téléphone" type="tel" autoComplete="tel" {...text('managerPhone')} />
            </div>
          )}

          {step.id === 'confirmation' && (
            <div className="space-y-5">
              <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-[12rem_1fr]">
                {[
                  ['Établissement', `${input.organizationName} (${input.shortName})`],
                  ['Type', input.organizationType ? ORGANIZATION_TYPE_LABELS[input.organizationType] : ''],
                  ['Ville', input.city],
                  ['Responsable', `${input.managerFirstName} ${input.managerLastName}`],
                  ['Contact', `${input.managerEmail} · ${input.managerPhone}`],
                ].map(([term, value]) => (
                  <div key={term} className="contents">
                    <dt className="text-slate-500">{term}</dt>
                    <dd className="font-medium break-words text-slate-900">{value}</dd>
                  </div>
                ))}
              </dl>
              <CheckboxField
                label="J'atteste que ces informations sont exactes et que je suis habilité à représenter l'établissement."
                checked={input.attestsAccuracy}
                error={errors.attestsAccuracy}
                disabled={submitting}
                onChange={(e) => update('attestsAccuracy', e.target.checked)}
              />
              <CheckboxField
                label="Je comprends que cette inscription ne vaut pas approbation et que la décision appartient à l'Autorité de gouvernance."
                checked={input.acknowledgesGovernance}
                error={errors.acknowledgesGovernance}
                disabled={submitting}
                onChange={(e) => update('acknowledgesGovernance', e.target.checked)}
              />
            </div>
          )}
        </Card>
      </form>
    </div>
  )
}
