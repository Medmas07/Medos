import { Alert, Badge, Button, Card, DemoBadge, EmptyState, PageHeader } from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import type { GovernanceDecision, OnboardingSnapshot, StepId } from '../types/onboarding'

interface DecisionViewProps {
  snapshot: OnboardingSnapshot
  onNavigate: (step: StepId) => void
}

/**
 * Displays the decision of the Governance / Ethics Authority on the application
 * (HC-059). The portal never makes, changes, or contests a decision; it names the
 * Authority, not the individual reviewer.
 */
export function DecisionView({ snapshot, onNavigate }: DecisionViewProps) {
  const { application, decision } = snapshot

  const header = (
    <PageHeader
      eyebrow="Étape 9 · Parcours d'adhésion"
      title="Décision de gouvernance"
      description="Décision de l'Autorité de gouvernance et d'éthique sur l'adhésion de votre établissement."
      actions={decision?.simulated ? <DemoBadge>Décision simulée</DemoBadge> : undefined}
    />
  )

  if (!application || application.status === 'draft') {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune décision"
            description="Une décision n'est rendue qu'après la transmission du dossier et sa revue humaine."
            action={
              <Button onClick={() => onNavigate(application ? 'automated-review' : 'registration')}>
                {application ? 'Aller à la revue automatisée' : "Aller à l'inscription"}
              </Button>
            }
          />
        </Card>
      </>
    )
  }

  if (!decision) {
    return (
      <>
        {header}
        <Card
          title="Décision en attente"
          actions={<Badge tone="info">En revue humaine</Badge>}
          footer={
            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => onNavigate('human-review')}>
                Suivre la validation humaine
              </Button>
            </div>
          }
        >
          <p className="text-slate-700">
            L'Autorité de gouvernance n'a pas encore rendu sa décision. Elle apparaîtra ici dès sa publication ; le
            portail ne peut ni la rendre ni l'anticiper.
          </p>
        </Card>
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        {decision.simulated && (
          <Alert tone="demo" title="Décision simulée pour la démonstration">
            Dans le scénario canonique, cette candidature est approuvée en direct depuis le Portail de gouvernance. Ce
            scénario montre la décision telle que l'établissement la reçoit ; elle n'a été rendue par aucune autorité
            réelle.
          </Alert>
        )}
        {decision.outcome === 'approved' ? (
          <ApprovedDecision decision={decision} onNavigate={onNavigate} />
        ) : (
          <RejectedDecision decision={decision} />
        )}
      </div>
    </>
  )
}

function DecisionRecord({ decision }: { decision: GovernanceDecision }) {
  const rows: [string, string][] = [
    ['Décision rendue par', "Autorité de gouvernance et d'éthique"],
    ['Date', formatDateTime(decision.decidedAt)],
    ['Référence', decision.id],
    ['Validité', decision.validUntil ? `Jusqu'au ${formatDateTime(decision.validUntil)}` : 'Sans limite de durée indiquée'],
  ]
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[12rem_1fr]">
      {rows.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-slate-500">{term}</dt>
          <dd className="font-medium break-words text-slate-900">{value}</dd>
        </div>
      ))}
      <div className="contents">
        <dt className="text-slate-500">Motivation</dt>
        <dd className="break-words text-slate-900">{decision.rationale}</dd>
      </div>
    </dl>
  )
}

function ApprovedDecision({ decision, onNavigate }: { decision: GovernanceDecision; onNavigate: (step: StepId) => void }) {
  return (
    <>
      <Card
        title="Adhésion approuvée"
        actions={<Badge tone="success">Approuvée</Badge>}
        footer={
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>Prochaine étape : la configuration de votre Hospital Node.</span>
            <Button onClick={() => onNavigate('node-configuration')}>Voir la configuration du nœud</Button>
          </div>
        }
      >
        <DecisionRecord decision={decision} />
      </Card>
      {decision.conditions.length > 0 && (
        <Alert tone="warning" title="Conditions fixées par l'Autorité">
          <ul className="list-disc space-y-1 pl-5">
            {decision.conditions.map((condition) => (
              <li key={condition}>{condition}</li>
            ))}
          </ul>
        </Alert>
      )}
    </>
  )
}

function RejectedDecision({ decision }: { decision: GovernanceDecision }) {
  return (
    <>
      <Card title="Candidature non approuvée" actions={<Badge tone="danger">Rejetée</Badge>}>
        <DecisionRecord decision={decision} />
      </Card>
      <Alert tone="neutral" title="Aucune action disponible dans le portail">
        La configuration et le téléchargement du Hospital Node restent verrouillés. Pour toute question sur cette
        décision, adressez-vous à l'Autorité de gouvernance et d'éthique.
      </Alert>
    </>
  )
}
