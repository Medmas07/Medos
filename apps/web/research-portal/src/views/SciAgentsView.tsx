import { useState, type ReactNode } from 'react'
import { Alert, Badge, Button, Card, DemoBadge, EmptyState, PageHeader } from '@hackcure/design-system'
import {
  citationKindLabels,
  confidenceDisplay,
  formatDateTime,
  investigationErrorLabels,
  investigationStatusDisplay,
} from '../presentation'
import {
  investigationRequest,
  sciAgentsOverview,
  type InvestigationEntry,
  type ResolvedFinding,
  type ResolvedHypothesis,
} from '../services/sciagents'
import type { PageId, ResearchSnapshot, SciAgentsCitation } from '../types/research'

interface SciAgentsViewProps {
  snapshot: ResearchSnapshot
  onNavigate: (page: PageId) => void
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-slate-900">{children}</dd>
    </div>
  )
}

function Boundary() {
  return (
    <Card
      title="Frontière avec SciAgents"
      description="SciAgents est un système externe existant : ce portail ne le réimplémente pas et l'interroge par un contrat versionné."
    >
      <ol className="grid gap-3 text-sm md:grid-cols-3">
        <li className="rounded-md border border-slate-200 p-3">
          <p className="font-semibold text-slate-900">1. Portail de Recherche</p>
          <p className="mt-1 text-slate-600">Prépare la question, des références opaques et deux concepts biomédicaux non identifiants.</p>
        </li>
        <li className="rounded-md border border-slate-200 p-3">
          <p className="font-semibold text-slate-900">2. Contrat HC-170 et adaptateur</p>
          <p className="mt-1 text-slate-600">
            <code className="text-xs">scientific-investigation.v1</code> ; l'adaptateur serveur (HC-171) est implémenté et la
            connexion du portail (HC-172) reste planifiée.
          </p>
        </li>
        <li className="rounded-md border border-slate-200 p-3">
          <p className="font-semibold text-slate-900">3. SciAgents (externe)</p>
          <p className="mt-1 text-slate-600">
            Renvoie hypothèses, éléments à l'appui, contradictions et citations, à usage de recherche uniquement.
          </p>
        </li>
      </ol>
      <p className="mt-3 text-sm text-slate-600">
        Aucun dossier patient, identifiant, résultat contrôlé ni donnée brute des Hospital Nodes ne part vers SciAgents : seuls
        les deux concepts biomédicaux sont transmis par l'adaptateur.
      </p>
    </Card>
  )
}

function CitationRefs({ citations, numberOf }: { citations: SciAgentsCitation[]; numberOf: (id: string) => number }) {
  return (
    <span className="ml-1 text-xs whitespace-nowrap text-slate-500">
      {citations.map((c) => (
        <a key={c.id} href={`#citation-${c.id}`} className="mr-1 text-brand-700 hover:underline" title={c.title}>
          [{numberOf(c.id)}]
        </a>
      ))}
    </span>
  )
}

function Findings({
  title,
  items,
  empty,
  numberOf,
}: {
  title: string
  items: ResolvedFinding[]
  empty: string
  numberOf: (id: string) => number
}) {
  return (
    <div>
      <h4 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">{title}</h4>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">{empty}</p>
      ) : (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {items.map(({ finding, citations }) => (
            <li key={finding.id}>
              {finding.summary}
              <CitationRefs citations={citations} numberOf={numberOf} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Hypothesis({ item, index, numberOf }: { item: ResolvedHypothesis; index: number; numberOf: (id: string) => number }) {
  const confidence = confidenceDisplay[item.hypothesis.confidence ?? 'unknown']
  return (
    <li className="rounded-lg border border-slate-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="min-w-0 font-medium text-slate-900">
          <span className="text-slate-500">Hypothèse {index + 1} · </span>
          {item.hypothesis.statement}
        </p>
        <Badge tone={confidence.tone}>{confidence.label}</Badge>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Findings title="Éléments à l'appui" items={item.evidence} empty="Aucun élément à l'appui cité." numberOf={numberOf} />
        <Findings title="Éléments contraires" items={item.contradictions} empty="Aucune contradiction relevée." numberOf={numberOf} />
      </div>
    </li>
  )
}

function Citations({ citations, onNavigate }: { citations: SciAgentsCitation[]; onNavigate: (page: PageId) => void }) {
  return (
    <Card title="Citations" description="Chaque élément renvoie à au moins une citation ; les publications de cette démonstration sont inventées.">
      <ol className="space-y-3 text-sm">
        {citations.map((c, index) => (
          <li key={c.id} id={`citation-${c.id}`} className="flex gap-3">
            <span className="text-slate-500">[{index + 1}]</span>
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-slate-900">{c.title}</span>
                <Badge tone={c.kind === 'controlled_result' ? 'success' : 'neutral'}>{citationKindLabels[c.kind]}</Badge>
              </div>
              <p className="text-slate-600">{c.source}</p>
              {c.controlledResultId && (
                <Button size="sm" variant="ghost" onClick={() => onNavigate('results')}>
                  Voir le résultat {c.controlledResultId}
                </Button>
              )}
              {c.url && (
                <a href={c.url} target="_blank" rel="noreferrer" className="text-brand-700 break-all hover:underline">
                  {c.url}
                </a>
              )}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  )
}

function InvestigationOutcome({ entry, onNavigate }: { entry: InvestigationEntry; onNavigate: (page: PageId) => void }) {
  const { investigation, hypotheses } = entry
  if (investigation.status === 'failed' && investigation.error) {
    return (
      <Alert tone="danger" title={investigationErrorLabels[investigation.error.code]}>
        {investigation.error.message} Aucune hypothèse n'a été produite.{' '}
        {investigation.error.retryable
          ? 'La question peut être soumise à nouveau une fois le portail connecté à SciAgents (HC-172).'
          : "SciAgents a refusé la demande : la reformuler avant de la soumettre à nouveau."}
      </Alert>
    )
  }
  if (investigation.status === 'queued' || investigation.status === 'running') {
    return (
      <Alert tone="info" title="Investigation en cours">
        SciAgents n'a pas encore répondu. Les hypothèses apparaîtront ici une fois l'investigation terminée.
      </Alert>
    )
  }
  if (entry.unresolved.length > 0 || !hypotheses || !investigation.result) {
    return (
      <Alert tone="danger" title="Résultat non affiché : références incohérentes">
        Certaines références ne correspondent à aucun élément de la réponse ({entry.unresolved.join(', ')}). Une affirmation
        non traçable n'est pas affichée.
      </Alert>
    )
  }
  const citations = investigation.result.citations
  const numberOf = (id: string) => citations.findIndex((c) => c.id === id) + 1
  return (
    <>
      <Card
        title="Hypothèses"
        description="Pistes proposées par SciAgents, avec leur niveau de confiance déclaré, les éléments qui les appuient et ceux qui les contredisent."
      >
        {hypotheses.length === 0 ? (
          <EmptyState title="Aucune hypothèse" description="SciAgents n'a proposé aucune piste pour cette question." />
        ) : (
          <ol className="space-y-3">
            {hypotheses.map((item, index) => (
              <Hypothesis key={item.hypothesis.id} item={item} index={index} numberOf={numberOf} />
            ))}
          </ol>
        )}
        <p className="mt-3 text-xs text-slate-500">
          La confiance est celle que SciAgents déclare ; elle ne valide pas l'hypothèse.
        </p>
      </Card>
      {citations.length > 0 && <Citations citations={citations} onNavigate={onNavigate} />}
    </>
  )
}

function InvestigationPanel({ entry, onNavigate }: { entry: InvestigationEntry; onNavigate: (page: PageId) => void }) {
  const { investigation, summary } = entry
  const status = investigationStatusDisplay[investigation.status]
  const { provenance } = investigation
  return (
    <div className="min-w-0 space-y-6">
      <Card
        title={investigation.question}
        description={`${summary.project.title} · investigation ${investigation.id} · ${formatDateTime(investigation.createdAt)}`}
        actions={<Badge tone={status.tone}>{status.label}</Badge>}
      />

      <Alert tone="warning" title="Pistes de recherche, pas des conclusions cliniques">
        Les réponses de SciAgents sont des hypothèses à examiner par le chercheur (
        <code className="text-xs">{investigation.clinicalUse}</code>) : elles ne constituent ni un diagnostic ni une
        recommandation, et ne deviennent jamais une donnée clinique ni une donnée versée à un dossier médical.
      </Alert>

      <InvestigationOutcome entry={entry} onNavigate={onNavigate} />

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Contexte transmis" description="Ce que la demande HC-170 peut porter : jamais de données brutes.">
          {entry.context.length === 0 ? (
            <p className="text-sm text-slate-500">Aucun résultat contrôlé n'accompagne la question.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {entry.context.map((c) => (
                <li key={c.controlledResultId} className="rounded-md border border-slate-200 p-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="text-xs text-slate-700">{c.controlledResultId}</code>
                    {c.released ? (
                      <Badge tone="success">Contrôle de divulgation réussi</Badge>
                    ) : (
                      <Badge tone="danger">Non publié : non transmissible</Badge>
                    )}
                  </div>
                  <p className="mt-1 text-slate-700">{c.summary}</p>
                </li>
              ))}
            </ul>
          )}
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-slate-700">Corps de la demande HC-170 (non envoyé)</summary>
            <pre className="mt-2 overflow-x-auto rounded-md bg-slate-50 p-3 text-xs text-slate-800">
              {JSON.stringify(investigationRequest(entry), null, 2)}
            </pre>
          </details>
        </Card>

        <Card title="Provenance">
          <dl className="space-y-3 text-sm">
            <Field label="Fournisseur">
              {provenance.provider.name}
              <span className="text-slate-500"> · version {provenance.provider.version ?? 'non communiquée'}</span>
            </Field>
            <Field label="Adaptateur">
              {provenance.adapter.name} {provenance.adapter.version}
              <span className="text-slate-500"> · aucun adaptateur réel n'existe encore (HC-171)</span>
            </Field>
            <Field label="Origine">
              {provenance.mocked ? <DemoBadge>Fixture simulée</DemoBadge> : 'SciAgents'}
            </Field>
            <Field label="Référence SciAgents">{provenance.upstreamRequestRef ?? 'Aucune (rien n’a été envoyé)'}</Field>
            <Field label="Mise à jour">{formatDateTime(investigation.updatedAt)}</Field>
            <Field label="Note">{provenance.note}</Field>
          </dl>
        </Card>
      </div>
    </div>
  )
}

/** SciAgents research panel (HC-102): fixture investigations from an external system, MOCKED. */
export function SciAgentsView({ snapshot, onNavigate }: SciAgentsViewProps) {
  const entries = sciAgentsOverview(snapshot)
  const [selectedId, setSelectedId] = useState(() => entries[0]?.investigation.id ?? '')
  const entry = entries.find((e) => e.investigation.id === selectedId) ?? entries[0]

  const header = (
    <PageHeader
      eyebrow="Assistance scientifique · HC-102"
      title="SciAgents"
      description="Explorez les hypothèses qu'un système scientifique externe propose à partir de votre question et de vos résultats contrôlés, avec leurs preuves, contradictions et citations."
      actions={<DemoBadge>Investigations fictives</DemoBadge>}
    />
  )

  if (snapshot.projects.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="Une investigation SciAgents se rattache à un projet de recherche."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="SciAgents simulé (D1)">
          Les investigations affichées sont des fixtures fictives : ce portail n'envoie rien à SciAgents et n'en reçoit rien.
          Ce ne sont pas des sorties réelles de SciAgents, et les publications citées sont inventées.
        </Alert>

        <Boundary />

        {entry ? (
          <>
            {entries.length > 1 && (
              <Card title="Vos investigations" description={`${entries.length} investigation(s), la plus récente d'abord.`}>
                <ul className="grid gap-2 md:grid-cols-2">
                  {entries.map((e) => (
                    <li key={e.investigation.id}>
                      <button
                        type="button"
                        aria-pressed={e.investigation.id === entry.investigation.id}
                        onClick={() => setSelectedId(e.investigation.id)}
                        className={`w-full rounded-lg border p-3 text-left text-sm focus:ring-2 focus:ring-brand-600/20 focus:outline-none ${
                          e.investigation.id === entry.investigation.id
                            ? 'border-brand-600 bg-brand-50'
                            : 'border-slate-200 bg-white hover:bg-slate-50'
                        }`}
                      >
                        <code className="text-xs text-slate-700">{e.investigation.id}</code>
                        <p className="mt-1 font-medium text-slate-900">{e.investigation.question}</p>
                        <p className="text-xs text-slate-500">{e.summary.project.title}</p>
                      </button>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            <InvestigationPanel entry={entry} onNavigate={onNavigate} />
          </>
        ) : (
          <Card>
            <EmptyState
              title="Aucune investigation"
              description="Soumettre une question à SciAgents sera possible une fois le portail connecté (HC-172). Aucune investigation fictive n'existe pour vos projets."
              action={
                <Button variant="secondary" onClick={() => onNavigate('results')}>
                  Voir les résultats contrôlés
                </Button>
              }
            />
          </Card>
        )}
      </div>
    </>
  )
}
