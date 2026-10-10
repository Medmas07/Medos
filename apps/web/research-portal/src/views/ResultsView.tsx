import { useState, type ReactNode } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  Table,
  type TableColumn,
} from '@hackcure/design-system'
import { columnDecimals, formatCell, formatDateTime, withheldReasonDisplay } from '../presentation'
import { controlledResultTable } from '../services/researchService'
import { resultsOverview, resultTimes, type ControlledResultEntry, type WithheldExecution } from '../services/results'
import type { PageId, ResearchSnapshot } from '../types/research'

interface ResultsViewProps {
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

function AggregateTable({ entry }: { entry: ControlledResultEntry }) {
  if (!entry.table) {
    return (
      <Alert tone="danger" title="Contrôle de divulgation échoué">
        L'agrégat n'a pas passé le contrôle de divulgation : aucune valeur n'est publiée.
      </Alert>
    )
  }
  const { columns, rows } = entry.table
  const tableColumns: TableColumn<(string | number)[]>[] = columns.map((header, index) => {
    const decimals = columnDecimals(rows.map((r) => r[index]))
    return {
      key: String(index),
      header,
      rowHeader: index === 0,
      align: rows.some((r) => typeof r[index] === 'number') ? 'right' : 'left',
      render: (row) => formatCell(row[index], decimals),
    }
  })
  return (
    <Table
      caption={`${entry.result.title} : agrégat publié après contrôle de divulgation`}
      columns={tableColumns}
      rows={rows}
      getRowKey={(row) => String(row[0])}
      empty={<EmptyState title="Aucune ligne" description="L'agrégat publié est vide." />}
    />
  )
}

function ResultPanel({ entry, onNavigate }: { entry: ControlledResultEntry; onNavigate: (page: PageId) => void }) {
  const { result, summary } = entry
  const { aggregatedAt, checkedAt } = resultTimes(entry)
  const fixtureRerun = entry.releases.some((e) => e.origin === 'session')
  return (
    <div className="min-w-0 space-y-6">
      <Card
        title={result.title}
        description={`${summary.project.title} · résultat ${result.id}`}
        actions={
          result.disclosureCheck === 'passed' ? (
            <Badge tone="success">Contrôle de divulgation réussi</Badge>
          ) : (
            <Badge tone="danger">Contrôle de divulgation échoué</Badge>
          )
        }
        flush
      >
        <dl className="grid gap-3 border-b border-slate-100 p-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
          <Field label="Effectif minimal par cellule">{result.minimumCellSize}</Field>
          <Field label="Hospital Nodes combinés">{entry.sourceOrganizations.length}</Field>
          <Field label="Lignes agrégées">{entry.table?.rows.length ?? 0}</Field>
          <Field label="Contrôlé le">{checkedAt ? formatDateTime(checkedAt) : 'Inconnu'}</Field>
        </dl>
        <AggregateTable entry={entry} />
      </Card>

      <Alert tone="warning" title="Résultat de recherche, pas une donnée clinique">
        Cet agrégat décrit une population, pas un patient : il ne constitue ni un diagnostic ni une recommandation, et
        n'est versé dans aucun dossier médical. Son interprétation relève du chercheur et du protocole autorisé.
      </Alert>

      <div className="hc-stagger grid gap-6 md:grid-cols-2">
        <Card title="Provenance">
          <dl className="space-y-3 text-sm">
            <Field label="Décision de gouvernance">{entry.source?.decisionId ?? summary.decision?.id ?? 'Inconnue'}</Field>
            <Field label="Exécution d'origine">
              {result.jobId}
              {entry.source?.notebookId && <span className="text-slate-500"> · notebook {entry.source.notebookId}</span>}
            </Field>
            <Field label="Agrégé le">{aggregatedAt ? formatDateTime(aggregatedAt) : 'Inconnu'}</Field>
            <Field label="Empreinte SHA-256 du code">
              <span className="text-xs break-all text-slate-700">
                {entry.source?.algorithmSha256 ? (
                  <code>{entry.source.algorithmSha256}</code>
                ) : (
                  'Non enregistrée pour cette exécution fictive.'
                )}
              </span>
            </Field>
            <Field label="Origine des données">{result.provenance}</Field>
          </dl>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => onNavigate('execution')}>
              Voir les exécutions
            </Button>
            <Button size="sm" variant="ghost" onClick={() => onNavigate('request-status')}>
              Voir la décision
            </Button>
          </div>
        </Card>

        <Card title="Hospital Nodes combinés" description="Chaque nœud a exécuté le code localement ; seul son agrégat est sorti.">
          <ul className="space-y-2 text-sm">
            {entry.sourceOrganizations.map((org) => (
              <li key={org.id} className="rounded-xl border border-slate-200 p-2">
                <span className="font-medium text-slate-900">{org.name}</span>
                {org.node && <code className="ml-2 text-xs text-slate-500">{org.node.id}</code>}
              </li>
            ))}
            {entry.sourceOrganizations.length === 0 && <li className="text-slate-500">Aucun Hospital Node enregistré.</li>}
          </ul>
          <h3 className="mt-5 text-sm font-semibold text-slate-900">Mises à disposition</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {entry.releases.map((e) => (
              <li key={e.id} className="text-slate-700">
                <code className="text-xs">{e.id}</code> · {formatDateTime(e.submittedAt)}
                <span className="text-slate-500">
                  {e.origin === 'fixture' ? ' · exécution fictive' : ' · espace de travail, résultat fictif non recalculé'}
                </span>
              </li>
            ))}
          </ul>
          {fixtureRerun && (
            <p className="mt-2 text-xs text-slate-500">
              Une exécution du notebook inchangé renvoie le même résultat fictif : rien n'est recalculé dans cette démonstration.
            </p>
          )}
        </Card>
      </div>

      <Card title="Aller plus loin">
        <p className="text-sm text-slate-600">
          SciAgents (système externe, non connecté à ce stade) explore des hypothèses à partir du résumé de ce résultat ;
          ses sorties restent des pistes à examiner par le chercheur.
        </p>
        <Button className="mt-3" size="sm" variant="secondary" onClick={() => onNavigate('sciagents')}>
          Ouvrir SciAgents
        </Button>
      </Card>
    </div>
  )
}

function WithheldList({ items, onNavigate }: { items: WithheldExecution[]; onNavigate: (page: PageId) => void }) {
  const columns: TableColumn<WithheldExecution>[] = [
    { key: 'id', header: 'Exécution', rowHeader: true, render: ({ execution }) => <code className="text-xs break-all">{execution.id}</code> },
    { key: 'project', header: 'Projet', render: ({ execution }) => execution.summary.project.title },
    {
      key: 'reason',
      header: 'Motif',
      render: ({ reason, execution }) => (
        <div className="space-y-1">
          <Badge tone={withheldReasonDisplay[reason].tone}>{withheldReasonDisplay[reason].label}</Badge>
          <p className="text-xs text-slate-500">{execution.error ?? withheldReasonDisplay[reason].detail}</p>
        </div>
      ),
    },
  ]
  return (
    <Card
      title="Exécutions sans résultat publié"
      description="Aucune valeur n'en est sortie des Hospital Nodes."
      actions={
        <Button size="sm" variant="ghost" onClick={() => onNavigate('execution')}>
          Voir les exécutions
        </Button>
      }
      flush
    >
      <Table caption="Exécutions sans résultat publié" columns={columns} rows={items} getRowKey={(i) => i.execution.id} />
    </Card>
  )
}

/** Research experiment result panel (HC-101): released controlled results, MOCKED fixtures. */
export function ResultsView({ snapshot, onNavigate }: ResultsViewProps) {
  const { results, withheld } = resultsOverview(snapshot, controlledResultTable)
  const [selectedId, setSelectedId] = useState(() => results[0]?.result.id ?? '')
  const entry = results.find((r) => r.result.id === selectedId) ?? results[0]

  const header = (
    <PageHeader
      eyebrow="Compute-to-Data · HC-101"
      title="Résultats contrôlés"
      description="Consultez les agrégats revenus des Hospital Nodes après agrégation et contrôle de divulgation, avec leur provenance. Aucune donnée individuelle n'en sort."
      actions={<DemoBadge>Résultats fictifs</DemoBadge>}
    />
  )

  if (snapshot.projects.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="Les résultats contrôlés apparaissent une fois un projet autorisé et une analyse exécutée."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  if (snapshot.pages.find((p) => p.id === 'results')?.status === 'locked') {
    return (
      <>
        {header}
        <Alert
          tone="neutral"
          title="Résultats verrouillés"
          actions={
            <Button variant="secondary" size="sm" onClick={() => onNavigate('request-status')}>
              Suivre les demandes
            </Button>
          }
        >
          Aucun de vos projets ne détient une autorisation de gouvernance valide : aucun résultat n'est consultable.
        </Alert>
      </>
    )
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Résultats simulés (D1)">
          Les résultats sont des fixtures fictives : rien n'est recalculé, et aucun Research Service, Governance Node ni
          Hospital Node n'est contacté. Ils ne sont pas des résultats scientifiques validés.
        </Alert>

        {entry ? (
          <>
            {results.length > 1 && (
              <Card title="Vos résultats" description={`${results.length} résultat(s), le plus récent d'abord.`}>
                <ul className="grid gap-2 md:grid-cols-2">
                  {results.map((r) => (
                    <li key={r.result.id}>
                      <button
                        type="button"
                        aria-pressed={r.result.id === entry.result.id}
                        onClick={() => setSelectedId(r.result.id)}
                        className={`w-full rounded-lg border p-3 text-left text-sm focus:ring-2 focus:ring-brand-600/20 focus:outline-none ${
                          r.result.id === entry.result.id ? 'border-brand-600 bg-brand-50' : 'border-slate-200 bg-surface hover:bg-brand-50/60'
                        }`}
                      >
                        <code className="text-xs text-slate-700">{r.result.id}</code>
                        <p className="mt-1 font-medium text-slate-900">{r.result.title}</p>
                        <p className="text-xs text-slate-500">{r.summary.project.title}</p>
                      </button>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            <ResultPanel entry={entry} onNavigate={onNavigate} />
          </>
        ) : (
          <Card>
            <EmptyState
              title="Aucun résultat contrôlé"
              description="Un résultat apparaît ici une fois une exécution terminée et son agrégat passé au contrôle de divulgation."
              action={<Button onClick={() => onNavigate('workspace')}>Ouvrir l'espace de travail</Button>}
            />
          </Card>
        )}

        {withheld.length > 0 && <WithheldList items={withheld} onNavigate={onNavigate} />}
      </div>
    </>
  )
}
