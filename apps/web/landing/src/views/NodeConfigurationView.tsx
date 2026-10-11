import type { ReactNode } from 'react'
import { Alert, Badge, Button, Card, DemoBadge, EmptyState, PageHeader } from '@hackcure/design-system'
import { DMI_HOSTING_LABELS, hasDmiAnswers, INTEGRATION_LABELS } from '../services/dmiService'
import { configFileJson, nodeConfiguration, type NodeConfigurationSummary } from '../services/nodeConfigService'
import { HOSTING_LABELS } from '../services/technicalService'
import type { OnboardingSnapshot, StepId } from '../types/onboarding'

interface NodeConfigurationViewProps {
  snapshot: OnboardingSnapshot
  onNavigate: (step: StepId) => void
}

export function NodeConfigurationView({ snapshot, onNavigate }: NodeConfigurationViewProps) {
  const availability = nodeConfiguration(snapshot)

  const header = (
    <PageHeader
      eyebrow="Hospital Node · Étape 10"
      title="Configuration du nœud"
      description="Configuration de votre Hospital Node, générée après l'approbation de votre adhésion. Le nœud fonctionnera chez vous, sous votre contrôle."
      actions={<DemoBadge>Configuration simulée</DemoBadge>}
    />
  )

  if (availability.kind !== 'ready') {
    const locked = {
      no_application: {
        title: 'Aucune candidature transmise',
        description: "La configuration est générée après l'approbation de votre candidature.",
        action: <Button onClick={() => onNavigate('registration')}>Aller à l'inscription</Button>,
      },
      awaiting_decision: {
        title: 'Disponible après approbation',
        description: "L'Autorité de gouvernance n'a pas encore approuvé votre adhésion ; aucune configuration n'est générée avant sa décision.",
        action: (
          <Button variant="secondary" onClick={() => onNavigate('decision')}>
            Voir la décision
          </Button>
        ),
      },
      rejected: {
        title: 'Aucune configuration',
        description: "La candidature n'a pas été approuvée : aucun Hospital Node n'est configuré.",
        action: (
          <Button variant="secondary" onClick={() => onNavigate('decision')}>
            Voir la décision
          </Button>
        ),
      },
    }[availability.kind]
    return (
      <>
        {header}
        <Card>
          <EmptyState title={locked.title} description={locked.description} action={locked.action} />
        </Card>
      </>
    )
  }

  return (
    <>
      {header}
      <ReadyConfiguration summary={availability.summary} snapshot={snapshot} onNavigate={onNavigate} />
    </>
  )
}

function Details({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[14rem_1fr]">
      {rows.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-slate-500">{term}</dt>
          <dd className="font-medium break-words text-slate-900">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function ReadyConfiguration({
  summary,
  snapshot,
  onNavigate,
}: {
  summary: NodeConfigurationSummary
  snapshot: OnboardingSnapshot
  onNavigate: (step: StepId) => void
}) {
  const { file, environment: q } = summary
  const notSet = <Badge tone="warning">À définir</Badge>
  return (
    <div className="space-y-6">
      <Alert tone="info" title="Aucun secret dans cette configuration">
        Elle ne contient ni mot de passe, ni clé, ni certificat. L'identité authentifiée du nœud n'est pas encore
        implémentée ; elle ne sera jamais transmise par ce portail.
      </Alert>
      {summary.blockers.length > 0 && (
        <Alert tone="warning" title="Configuration de démonstration incomplète">
          <ul className="list-disc space-y-1 pl-5">
            {summary.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Identité du nœud">
          <Details
            rows={[
              ['Référence du nœud', <code key="n">{file.node_ref}</code>],
              ['Établissement', snapshot.organization.name],
              ['Référence de l’établissement', <code key="o">{file.organization_ref}</code>],
              ["Décision d'approbation", <code key="d">{summary.approvalDecisionRef}</code>],
            ]}
          />
        </Card>
        <Card title="Réseau et fédération">
          <Details
            rows={[
              ['Port local', file.port ?? notSet],
              ['Adresse de démonstration', summary.federationBaseUrl ?? notSet],
              ['Contrat de fédération', `Version ${summary.federationContractVersion}`],
              ['Stockage local', <code key="s">{file.storage_dir}</code>],
            ]}
          />
          <p className="mt-4 text-xs text-slate-500">
            L'inscription du nœud au registre de fédération cite cette décision d'approbation ; elle n'est pas effectuée
            par ce portail.
          </p>
        </Card>
        <Card title="Environnement déclaré">
          {q ? (
            <Details
              rows={[
                ['Hébergement', HOSTING_LABELS[q.hostingType]],
                ["Système d'exploitation", q.operatingSystem],
                ['Ressources', `${q.cpuCores} cœurs · ${q.memoryGb} Go · ${q.storageGb} Go de stockage`],
                ['Conteneurs', q.containerRuntimeAvailable ? 'Possibles' : 'Non disponibles'],
              ]}
            />
          ) : (
            <p className="text-slate-600">Questionnaire technique non renseigné.</p>
          )}
        </Card>
        <Card title="Adaptateur DMI local" actions={<Badge tone="neutral">À configurer chez vous</Badge>}>
          {q && hasDmiAnswers(q) ? (
            <Details
              rows={[
                ['DMI / SIH', q.dmiSystem],
                ['Hébergement du DMI', q.dmiHosting ? DMI_HOSTING_LABELS[q.dmiHosting] : '—'],
                ["Méthodes d'intégration", (q.integrationMethods ?? []).map((m) => INTEGRATION_LABELS[m].label).join(', ')],
              ]}
            />
          ) : (
            <p className="text-slate-600">Informations DMI non renseignées.</p>
          )}
          <p className="mt-4 text-xs text-slate-500">
            L'adaptateur DMI s'exécute dans votre Hospital Node ; sa configuration n'est pas encore implémentée et reste
            locale. Aucun service central ne se connecte à votre DMI.
          </p>
        </Card>
      </div>

      <Card
        title="Aperçu du fichier de configuration"
        description="Champs lus et validés par le Hospital Node au démarrage (variable HOSPITAL_NODE_CONFIG)."
        footer={
          <div className="flex justify-end">
            <Button onClick={() => onNavigate('node-download')}>Continuer : téléchargement du nœud</Button>
          </div>
        }
      >
        <pre className="overflow-x-auto hc-chrome rounded-xl bg-chrome p-4 text-xs leading-relaxed text-ink">
          <code>{configFileJson(file)}</code>
        </pre>
      </Card>
    </div>
  )
}
