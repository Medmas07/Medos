import { useState, type FormEvent, type ReactNode } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  TextField,
} from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import {
  applyProfile,
  canEditProfile,
  demoProfile,
  inputFromProfile,
  LEGAL_STATUS_LABELS,
  profileInputFrom,
  saveProfile,
  validateProfile,
  type ProfileErrors,
  type ProfileField,
  type ProfileInput,
} from '../services/profileService'
import type { AdministrativeProfile, OnboardingSnapshot, StepId } from '../types/onboarding'

interface ProfileViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make this save fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

const statusOptions = (Object.keys(LEGAL_STATUS_LABELS) as AdministrativeProfile['legalStatus'][]).map(
  (value) => ({ value, label: LEGAL_STATUS_LABELS[value] }),
)

export function ProfileView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: ProfileViewProps) {
  const { application } = snapshot
  const editable = canEditProfile(application)
  const profile = application?.administrativeProfile ?? null
  const [editing, setEditing] = useState(editable && !profile)
  const [justSaved, setJustSaved] = useState(false)

  const header = (
    <PageHeader
      eyebrow="Étape 2 · Parcours d'adhésion"
      title="Profil de l'établissement"
      description="Informations administratives transmises avec votre candidature : identité légale, adresse, contacts et responsables."
      actions={<DemoBadge>Profil simulé</DemoBadge>}
    />
  )

  if (!application) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune inscription"
            description="Inscrivez d'abord votre établissement ; le profil complète ensuite votre dossier."
            action={<Button onClick={() => onNavigate('registration')}>Aller à l'inscription</Button>}
          />
        </Card>
      </>
    )
  }

  if (editing) {
    return (
      <>
        {header}
        <ProfileForm
          snapshot={snapshot}
          consumeSimulatedFailure={consumeSimulatedFailure}
          onCancel={profile ? () => setEditing(false) : undefined}
          onSaved={(next) => {
            onUpdated(next)
            setEditing(false)
            setJustSaved(true)
          }}
        />
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        {justSaved && (
          <Alert
            tone="success"
            title="Profil enregistré (simulation)"
            actions={<Button onClick={() => onNavigate('documents')}>Continuer : documents administratifs</Button>}
          >
            Le profil est conservé dans cette page jusqu'à son rechargement ; il n'est transmis à aucun service réel.
          </Alert>
        )}
        {!editable && (
          <Alert tone="neutral" title="Profil verrouillé">
            Votre candidature a été transmise pour revue : le profil ne peut plus être modifié depuis le portail.
          </Alert>
        )}
        {profile ? (
          <ProfileSummary
            profile={profile}
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
              title="Profil non disponible"
              description="Cette candidature a été instruite avant l'introduction du profil administratif."
            />
          </Card>
        )}
      </div>
    </>
  )
}

function Details({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[12rem_1fr]">
      {rows.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-slate-500">{term}</dt>
          <dd className="font-medium break-words text-slate-900">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function ProfileSummary({ profile, onEdit }: { profile: AdministrativeProfile; onEdit?: () => void }) {
  const { address, legalRepresentative, dataProtectionOfficer, securityContact } = profile
  const securityValue = securityContact ? (
    `${securityContact.fullName} · ${securityContact.email}`
  ) : (
    <Badge tone="warning">Non désigné</Badge>
  )
  return (
    <>
      {!securityContact && (
        <Alert tone="warning" title="Aucun contact sécurité distinct">
          Recommandé : désignez un contact dédié aux incidents de sécurité du Hospital Node. Ce n'est pas
          bloquant pour l'inscription.
        </Alert>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Identité légale"
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
              ['Raison sociale', profile.legalName],
              ['Statut juridique', LEGAL_STATUS_LABELS[profile.legalStatus]],
              ['Identifiant administratif', profile.registrationNumber],
              ['Capacité', `${profile.bedCapacity} lits`],
            ]}
          />
        </Card>
        <Card title="Adresse et contact">
          <Details
            rows={[
              ['Adresse', address.street],
              ['Ville', `${address.postalCode} ${address.city}`],
              ['Gouvernorat', address.governorate],
              ['Téléphone', profile.phone],
              ['E-mail', profile.email],
            ]}
          />
        </Card>
        <Card title="Responsables" className="lg:col-span-2" footer={`Mis à jour le ${formatDateTime(profile.updatedAt)}`}>
          <Details
            rows={[
              ['Représentant légal', `${legalRepresentative.fullName} — ${legalRepresentative.role}`],
              ['Protection des données', `${dataProtectionOfficer.fullName} · ${dataProtectionOfficer.email}`],
              ['Contact sécurité', securityValue],
            ]}
          />
        </Card>
      </div>
    </>
  )
}

type Save = { kind: 'idle' } | { kind: 'saving' } | { kind: 'failed'; message: string }

function ProfileForm({
  snapshot,
  consumeSimulatedFailure,
  onCancel,
  onSaved,
}: {
  snapshot: OnboardingSnapshot
  consumeSimulatedFailure: () => boolean
  onCancel?: () => void
  onSaved: (snapshot: OnboardingSnapshot) => void
}) {
  const [input, setInput] = useState<ProfileInput>(() => profileInputFrom(snapshot))
  const [errors, setErrors] = useState<ProfileErrors>({})
  const [save, setSave] = useState<Save>({ kind: 'idle' })
  const saving = save.kind === 'saving'

  const field = (name: ProfileField, extra: { required?: boolean } = { required: true }) => ({
    value: input[name],
    error: errors[name],
    disabled: saving,
    required: extra.required,
    onChange: (e: { target: { value: string } }) => {
      setInput((current) => ({ ...current, [name]: e.target.value }))
      setErrors((current) => ({ ...current, [name]: undefined }))
    },
  })

  const submit = async () => {
    const found = validateProfile(input)
    setErrors(found)
    if (Object.keys(found).length > 0) return
    setSave({ kind: 'saving' })
    try {
      const result = await saveProfile(input, { simulateFailure: consumeSimulatedFailure() })
      if (result.kind === 'rejected') {
        setErrors(result.errors)
        setSave({ kind: 'idle' })
        return
      }
      onSaved(applyProfile(snapshot, result.profile))
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
          title="Profil non enregistré"
          actions={<Button variant="secondary" onClick={() => void submit()}>Réessayer</Button>}
        >
          {save.message} Vos informations sont conservées.
        </Alert>
      )}
      {errorCount > 0 && (
        <Alert tone="warning" title="Profil incomplet">
          {errorCount} champ{errorCount > 1 ? 's' : ''} à corriger.
        </Alert>
      )}

      <Card
        title="Identité légale"
        actions={
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={saving}
            onClick={() => {
              setInput(inputFromProfile(demoProfile()))
              setErrors({})
            }}
          >
            Remplir avec l'exemple fictif
          </Button>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Raison sociale" className="sm:col-span-2" {...field('legalName')} />
          <SelectField label="Statut juridique" placeholder="Choisir…" options={statusOptions} {...field('legalStatus')} />
          <TextField
            label="Identifiant administratif"
            hint="Numéro d'enregistrement de l'établissement."
            {...field('registrationNumber')}
          />
          <TextField label="Capacité (lits)" inputMode="numeric" {...field('bedCapacity')} />
        </div>
      </Card>

      <Card title="Adresse et contact">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Adresse" className="sm:col-span-2" autoComplete="street-address" {...field('street')} />
          <TextField label="Code postal" inputMode="numeric" autoComplete="postal-code" {...field('postalCode')} />
          <TextField label="Ville" autoComplete="address-level2" {...field('city')} />
          <TextField label="Gouvernorat" autoComplete="address-level1" {...field('governorate')} />
          <TextField label="Téléphone de l'établissement" type="tel" {...field('phone')} />
          <TextField label="E-mail de l'établissement" type="email" className="sm:col-span-2" {...field('email')} />
        </div>
      </Card>

      <Card
        title="Responsables"
        footer={
          <div className="flex flex-wrap justify-end gap-2">
            {onCancel && (
              <Button type="button" variant="secondary" disabled={saving} onClick={onCancel}>
                Annuler
              </Button>
            )}
            <Button type="submit" loading={saving}>
              Enregistrer le profil
            </Button>
          </div>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Représentant légal" {...field('representativeName')} />
          <TextField label="Fonction du représentant" {...field('representativeRole')} />
          <TextField label="Délégué à la protection des données" {...field('dpoName')} />
          <TextField label="E-mail du délégué" type="email" {...field('dpoEmail')} />
          <TextField
            label="Contact sécurité (recommandé)"
            hint="Facultatif : personne à joindre en cas d'incident de sécurité."
            {...field('securityName', {})}
          />
          <TextField label="E-mail du contact sécurité" type="email" {...field('securityEmail', {})} />
        </div>
      </Card>
    </form>
  )
}
