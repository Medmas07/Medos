/**
 * Notifications View — HC-200: Notification UI fixtures at D1.
 *
 * Displays the Governance reviewer's notification center with:
 * - summary counts and unread badge
 * - filter tabs by notification type
 * - individual mark-as-read and bulk "mark all read"
 * - timeline rendering using the design-system Timeline
 * - empty state for filters with no results
 * - demo banner reminding this is MOCKED delivery
 *
 * All data comes from demo-data/notifications.json via governanceService.
 * Mark-as-read is SIMULATED (in-memory, session-only).
 */
import { useState, useSyncExternalStore } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  Timeline,
  type TimelineItem,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import {
  applyReadOverrides,
  countNotifications,
  filterNotifications,
  notificationRows,
  notificationStore,
  NOTIFICATION_FILTER_LABELS,
  NOTIFICATION_ICON,
  NOTIFICATION_TONE,
  NOTIFICATION_TYPE_LABELS,
  type NotificationFilter,
  type NotificationType,
} from '../../services/notificationService'

const ALL_FILTERS: NotificationFilter[] = [
  'all',
  'review_requested',
  'alert',
  'access_granted',
  'new_record',
  'delegation_granted',
  'request_status',
  'job_completed',
]

/** Tone mapping for the design-system's `Badge tone` and `Timeline marker`. */
const FILTER_BADGE_TONE: Record<NotificationFilter, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
  all: 'neutral',
  access_granted: 'success',
  new_record: 'info',
  delegation_granted: 'info',
  request_status: 'neutral',
  alert: 'danger',
  review_requested: 'warning',
  job_completed: 'success',
}

export function NotificationsView() {
  const [filter, setFilter] = useState<NotificationFilter>('all')

  // Re-render when notifications are marked read.
  useSyncExternalStore(notificationStore.subscribe, () => notificationStore.getSnapshot())

  // Load all notifications for the demo reviewer (usr-olfa) and apply session overrides.
  const rawNotifications = applyReadOverrides(governanceService.getReviewerNotifications('usr-olfa'))
  const allRows = notificationRows(rawNotifications)
  const counts = countNotifications(allRows)
  const filteredRows = filterNotifications(allRows, filter)

  const handleMarkRead = (id: string) => notificationStore.markRead(id)
  const handleMarkAllRead = () => notificationStore.markAllRead(rawNotifications)
  const handleResetDemo = () => notificationStore.reset()

  // Build Timeline items from the filtered rows.
  const timelineItems: TimelineItem[] = filteredRows.map((row) => ({
    id: row.notification.id,
    title: (
      <span className="flex items-center gap-2">
        <span>{row.icon}</span>
        <span className={row.notification.read ? 'text-slate-500' : 'font-semibold text-slate-900'}>
          {row.notification.title}
        </span>
        {!row.notification.read && (
          <Badge tone="warning" dot>
            Non lu
          </Badge>
        )}
      </span>
    ),
    timestamp: row.relativeTime,
    dateTime: row.notification.createdAt,
    description: (
      <div className="space-y-1.5">
        <p className={row.notification.read ? 'text-slate-400' : 'text-slate-700'}>
          {row.notification.body}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={NOTIFICATION_TONE[row.typedType]}>{row.label}</Badge>
          {row.notification.relatedId && (
            <span className="font-mono text-[11px] text-slate-400">{row.notification.relatedId}</span>
          )}
          {!row.notification.read && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => handleMarkRead(row.notification.id)}
            >
              Marquer comme lu
            </Button>
          )}
        </div>
      </div>
    ),
    tone: row.notification.read ? 'neutral' : NOTIFICATION_TONE[row.typedType],
    current: !row.notification.read,
  }))

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Centre de Notifications"
        title="Notifications de Gouvernance"
        description="Alertes, dossiers assignés et mises à jour pour les réviseurs de l'Autorité de Gouvernance."
        actions={
          <div className="flex gap-2">
            {counts.unread > 0 && (
              <Button size="sm" variant="primary" onClick={handleMarkAllRead}>
                Tout marquer lu ({counts.unread})
              </Button>
            )}
            <Button size="sm" variant="secondary" onClick={handleResetDemo}>
              Réinitialiser la démo
            </Button>
            <DemoBadge>Données fictives — Aucune notification réellement envoyée</DemoBadge>
          </div>
        }
      />

      {/* Architecture Invariant */}
      <Alert tone="info" title="Notification Service — D1 MOCKED">
        Les notifications sont lues depuis les fixtures fictives (demo-data/notifications.json). Aucun broker,
        WebSocket ou service de livraison n'est connecté. Le marquage « lu » est simulé en mémoire et réinitialisé
        au rechargement de la page.
      </Alert>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
        {ALL_FILTERS.filter((f) => f !== 'all').map((type) => {
          const t = type as NotificationType
          const count = counts[t]
          return (
            <button
              key={t}
              type="button"
              className={`text-left w-full rounded-lg border p-3 text-xs transition-all hover:scale-[1.02] focus:outline-none ${
                filter === t
                  ? 'border-brand-300 bg-brand-50 ring-2 ring-brand-200'
                  : 'border-slate-200 bg-white'
              }`}
              onClick={() => setFilter(filter === t ? 'all' : t)}
            >
              <div className="flex items-center gap-1.5">
                <span>{NOTIFICATION_ICON[t]}</span>
                <span className="font-semibold text-slate-700 truncate">{NOTIFICATION_TYPE_LABELS[t]}</span>
              </div>
              <div className="mt-1 text-lg font-bold text-slate-900">{count}</div>
            </button>
          )
        })}
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {ALL_FILTERS.map((f) => {
          const count = f === 'all' ? counts.all : counts[f as NotificationType]
          return (
            <Button
              key={f}
              size="sm"
              variant={filter === f ? 'primary' : 'secondary'}
              onClick={() => setFilter(f)}
            >
              {NOTIFICATION_FILTER_LABELS[f]}
              {count > 0 && (
                <Badge tone={FILTER_BADGE_TONE[f]} className="ml-1.5">
                  {count}
                </Badge>
              )}
            </Button>
          )
        })}
      </div>

      {/* Notification Timeline */}
      <Card
        title={`Notifications${filter !== 'all' ? ` — ${NOTIFICATION_FILTER_LABELS[filter]}` : ''}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={counts.unread > 0 ? 'warning' : 'success'} dot>
              {counts.unread > 0 ? `${counts.unread} non lue(s)` : 'Toutes lues'}
            </Badge>
            <Badge tone="neutral">{counts.all} totale(s)</Badge>
          </div>
        }
      >
        {filteredRows.length === 0 ? (
          <EmptyState
            title="Aucune notification"
            description={
              filter === 'all'
                ? 'Aucune notification dans le jeu de démonstration pour ce réviseur.'
                : `Aucune notification de type « ${NOTIFICATION_FILTER_LABELS[filter]} » trouvée.`
            }
            action={
              filter !== 'all' ? (
                <Button size="sm" variant="secondary" onClick={() => setFilter('all')}>
                  Voir toutes les notifications
                </Button>
              ) : undefined
            }
          />
        ) : (
          <Timeline label="Notifications de gouvernance" items={timelineItems} className="text-sm" />
        )}
      </Card>

      {/* Notification Details Table */}
      <Card title="Détail des Notifications" flush>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left">
                <th className="px-4 py-2.5 font-semibold text-slate-600">Statut</th>
                <th className="px-4 py-2.5 font-semibold text-slate-600">Type</th>
                <th className="px-4 py-2.5 font-semibold text-slate-600">Titre</th>
                <th className="px-4 py-2.5 font-semibold text-slate-600">Corps</th>
                <th className="px-4 py-2.5 font-semibold text-slate-600">Réf.</th>
                <th className="px-4 py-2.5 font-semibold text-slate-600">Date</th>
                <th className="px-4 py-2.5 font-semibold text-slate-600">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr
                  key={row.notification.id}
                  className={`border-b border-slate-100 transition-colors ${
                    row.notification.read ? 'bg-white' : 'bg-amber-50/30'
                  }`}
                >
                  <td className="px-4 py-2.5">
                    {row.notification.read ? (
                      <span className="inline-flex items-center gap-1 text-slate-400">
                        <span className="size-2 rounded-full bg-slate-300" /> Lu
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 font-semibold text-amber-600">
                        <span className="size-2 rounded-full bg-amber-500 animate-pulse" /> Non lu
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={NOTIFICATION_TONE[row.typedType]}>
                      {row.icon} {row.label}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5 font-medium text-slate-900">{row.notification.title}</td>
                  <td className="px-4 py-2.5 max-w-xs truncate text-slate-600" title={row.notification.body}>
                    {row.notification.body}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-slate-400">
                    {row.notification.relatedId ?? '—'}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500">
                    {new Date(row.notification.createdAt).toLocaleDateString('fr-TN', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                    })}
                  </td>
                  <td className="px-4 py-2.5">
                    {!row.notification.read ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleMarkRead(row.notification.id)}
                      >
                        Lu ✓
                      </Button>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
