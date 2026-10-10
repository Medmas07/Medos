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
import { formatDate, formatDateTime, requestStatusDisplay } from '../presentation'
import type { PageId, ProjectSummary, ResearchSnapshot } from '../types/research'

interface HomeViewProps {
  snapshot: ResearchSnapshot
  onNavigate: (page: PageId) => void
}

/** Landing page of the shell: the researcher's projects and the Compute-to-Data boundary. */
export function HomeView({ snapshot, onNavigate }: HomeViewProps) {
  const { organization, projects, notifications } = snapshot

  const columns: TableColumn<ProjectSummary>[] = [
    {
      key: 'title',
      header: 'Projet',
      rowHeader: true,
      render: ({ project }) => (
        <>
          <span className="font-medium text-slate-900">{project.title}</span>
          <span className="block text-xs text-slate-500">
            {project.id} · créé le {formatDate(project.createdAt)}
          </span>
        </>
      ),
    },
    {
      key: 'hospitals',
      header: 'Établissements',
      render: ({ participatingOrganizations }) =>
        participatingOrganizations.map((o) => o.shortName).join(', ') || '—',
    },
    {
      key: 'request',
      header: "Demande d'accès",
      render: ({ request }) => {
        const display = requestStatusDisplay[request?.status ?? 'not_submitted']
        return <Badge tone={display.tone}>{display.label}</Badge>
      },
    },
    {
      key: 'decision',
      header: 'Décision de gouvernance',
      render: ({ decision }) =>
        decision ? (
          <span className="text-xs text-slate-600">
            {decision.id} · {formatDate(decision.decidedAt)}
            {decision.validUntil && <> · valable jusqu'au {formatDate(decision.validUntil)}</>}
          </span>
        ) : (
          <span className="text-xs text-slate-500">Attendue</span>
        ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="Recherche gouvernée · Compute-to-Data"
        title="Accueil"
        description={`Projets de recherche de ${organization.name}, de la demande d'accès aux résultats contrôlés.`}
      />

      <Alert tone="info" title="Le code va aux données, pas l'inverse" className="mb-6">
        Les analyses sont exécutées dans les Hospital Nodes autorisés ; seuls des résultats agrégés et
        contrôlés reviennent. Aucune donnée individuelle n'est téléchargeable depuis ce portail. Chaque
        demande d'accès est décidée par l'Autorité de gouvernance et d'éthique ; ni ce portail ni
        l'opérateur de la plateforme ne peuvent l'autoriser.
      </Alert>

      <Card
        title="Mes projets de recherche"
        description="États dérivés des données fictives HC-005."
        actions={<DemoBadge>Fictif</DemoBadge>}
        flush
        className="mb-6"
      >
        <Table
          caption="Projets de recherche du chercheur"
          columns={columns}
          rows={projects}
          getRowKey={({ project }) => project.id}
          empty={
            <EmptyState
              title="Aucun projet de recherche"
              description="Créez un projet pour décrire votre protocole, votre population et les variables demandées."
              action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
            />
          }
        />
      </Card>

      <Card title="Notifications" actions={<DemoBadge>Simulées</DemoBadge>}>
        {notifications.length === 0 ? (
          <EmptyState title="Aucune notification" />
        ) : (
          <ul className="space-y-3">
            {notifications.map((n) => (
              <li key={n.id}>
                <p className="font-medium text-slate-900">{n.title}</p>
                <p className="text-slate-600">{n.body}</p>
                <p className="text-xs text-slate-500">{formatDateTime(n.createdAt)}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
