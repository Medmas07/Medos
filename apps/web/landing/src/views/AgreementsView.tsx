import { useState } from 'react'
import { Alert, Badge, Button, Card, CheckboxField, DemoBadge, EmptyState, PageHeader } from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import {
  acceptAgreement,
  AGREEMENT_TEMPLATES,
  agreementChecklist,
  applyAcceptance,
  applyWithdrawal,
  canChangeAgreements,
  type AgreementTemplate,
} from '../services/agreementService'
import type { ApplicationAgreement, OnboardingSnapshot, StepId } from '../types/onboarding'

interface AgreementsViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make this acceptance fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

export function AgreementsView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: AgreementsViewProps) {
  const { application, manager } = snapshot
  const header = (
    <PageHeader
      eyebrow="Étape 4 · Parcours d'adhésion"
      title="Accords"
      description="Accords à accepter pour rejoindre l'écosystème fédéré. Chaque acceptation est enregistrée avec la version du texte et son signataire."
      actions={<DemoBadge>Acceptation simulée</DemoBadge>}
    />
  )

  if (!application) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune inscription"
            description="Inscrivez d'abord votre établissement pour accepter les accords."
            action={<Button onClick={() => onNavigate('registration')}>Aller à l'inscription</Button>}
          />
        </Card>
      </>
    )
  }

  const editable = canChangeAgreements(application)
  const checklist = agreementChecklist(application)
  const accepted = checklist.filter((a) => a.accepted).length
  const complete = accepted === checklist.length
  const signatoryName = (id?: string) =>
    id === manager.id ? `${manager.firstName} ${manager.lastName}` : (id ?? 'signataire inconnu')

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Textes de démonstration">
          Les accords présentés sont des résumés fictifs, sans valeur juridique. L'acceptation est conservée dans cette
          page jusqu'à son rechargement et n'engage aucun établissement réel.
        </Alert>
        {!editable && (
          <Alert tone="neutral" title="Accords verrouillés">
            Votre candidature a été transmise : les acceptations enregistrées ne peuvent plus être modifiées depuis le
            portail.
          </Alert>
        )}
        {editable && complete && (
          <Alert
            tone="success"
            title="Tous les accords sont acceptés"
            actions={<Button onClick={() => onNavigate('technical')}>Continuer : questionnaire technique</Button>}
          >
            Ils seront joints à votre candidature. Leur acceptation ne vaut pas approbation de l'adhésion.
          </Alert>
        )}
        <p className="text-sm text-slate-600">
          {accepted} / {checklist.length} accords acceptés
        </p>
        {AGREEMENT_TEMPLATES.map((template) => (
          <AgreementCard
            key={template.code}
            template={template}
            agreement={checklist.find((a) => a.code === template.code)!}
            editable={editable}
            signatoryName={signatoryName}
            onAccept={async (confirmed) => {
              const record = await acceptAgreement(template.code, confirmed, manager.id, {
                simulateFailure: consumeSimulatedFailure(),
              })
              onUpdated(applyAcceptance(snapshot, record))
            }}
            onWithdraw={() => onUpdated(applyWithdrawal(snapshot, template.code))}
          />
        ))}
      </div>
    </>
  )
}

type Submit = { kind: 'idle' } | { kind: 'saving' } | { kind: 'failed'; message: string }

function AgreementCard({
  template,
  agreement,
  editable,
  signatoryName,
  onAccept,
  onWithdraw,
}: {
  template: AgreementTemplate
  agreement: ApplicationAgreement
  editable: boolean
  signatoryName: (id?: string) => string
  onAccept: (confirmed: boolean) => Promise<void>
  onWithdraw: () => void
}) {
  const [confirmed, setConfirmed] = useState(false)
  const [submit, setSubmit] = useState<Submit>({ kind: 'idle' })
  const saving = submit.kind === 'saving'

  const accept = async () => {
    setSubmit({ kind: 'saving' })
    try {
      await onAccept(confirmed)
      setSubmit({ kind: 'idle' })
      setConfirmed(false)
    } catch (error) {
      setSubmit({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
    }
  }

  const outdated = agreement.accepted && agreement.version !== undefined && agreement.version !== template.version

  return (
    <Card
      title={template.title}
      description={`Version ${template.version} · ${template.summary}`}
      actions={
        <Badge tone={agreement.accepted ? 'success' : 'warning'}>{agreement.accepted ? 'Accepté' : 'À accepter'}</Badge>
      }
      footer={
        agreement.accepted ? (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>
              Accepté
              {agreement.acceptedAt ? ` le ${formatDateTime(agreement.acceptedAt)}` : ''} par{' '}
              {signatoryName(agreement.acceptedById)}
              {agreement.version ? ` (version ${agreement.version})` : ''}.
            </span>
            {editable && (
              <Button size="sm" variant="ghost" onClick={onWithdraw}>
                Retirer l'acceptation
              </Button>
            )}
          </div>
        ) : editable ? (
          <div className="space-y-3">
            {submit.kind === 'failed' && (
              <Alert tone="danger" title="Acceptation non enregistrée">
                {submit.message}
              </Alert>
            )}
            <CheckboxField
              label={`J'ai lu l'accord « ${template.title} » (version ${template.version}) et je l'accepte au nom de l'établissement.`}
              checked={confirmed}
              disabled={saving}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <div className="flex justify-end">
              <Button disabled={!confirmed} loading={saving} onClick={() => void accept()}>
                {submit.kind === 'failed' ? 'Réessayer' : "Accepter l'accord"}
              </Button>
            </div>
          </div>
        ) : (
          'Non accepté.'
        )
      }
    >
      <ul className="list-disc space-y-1.5 pl-5 text-slate-700">
        {template.clauses.map((clause) => (
          <li key={clause}>{clause}</li>
        ))}
      </ul>
      {outdated && (
        <Alert tone="warning" title="Version différente" className="mt-4">
          La version acceptée ({agreement.version}) diffère de la version en vigueur ({template.version}).
        </Alert>
      )}
    </Card>
  )
}
