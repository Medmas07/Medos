/**
 * Notification service for the Governance Portal (HC-200).
 *
 * Consumes canonical fictional fixtures from demo-data/notifications.json,
 * provides typed rows, filtering, sorting, mark-as-read (SIMULATED, in-memory),
 * and badge counts. Uses the same in-memory session pattern as reviewStore.
 *
 * MOCKED — no real notification delivery. No real patient data.
 */

import type { GovernanceNotification } from '../types/governance'

// ─── Type vocabulary ────────────────────────────────────────────────────────

export type NotificationType =
  | 'access_granted'
  | 'new_record'
  | 'delegation_granted'
  | 'request_status'
  | 'alert'
  | 'review_requested'
  | 'job_completed'

export type NotificationFilter = 'all' | NotificationType

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  access_granted: 'Accès accordé',
  new_record: 'Nouveau dossier',
  delegation_granted: 'Délégation',
  request_status: 'Suivi de demande',
  alert: 'Alerte clinique',
  review_requested: 'Revue demandée',
  job_completed: 'Exécution terminée',
}

export const NOTIFICATION_FILTER_LABELS: Record<NotificationFilter, string> = {
  all: 'Toutes',
  ...NOTIFICATION_TYPE_LABELS,
}

/** Visual tone used by the design system Badge / Timeline marker. */
export type NotificationTone = 'info' | 'success' | 'warning' | 'danger' | 'neutral'

export const NOTIFICATION_TONE: Record<NotificationType, NotificationTone> = {
  access_granted: 'success',
  new_record: 'info',
  delegation_granted: 'info',
  request_status: 'neutral',
  alert: 'danger',
  review_requested: 'warning',
  job_completed: 'success',
}

/** SVG-icon identifier for each notification type. */
export const NOTIFICATION_ICON: Record<NotificationType, string> = {
  access_granted: '🔓',
  new_record: '📋',
  delegation_granted: '🤝',
  request_status: '📊',
  alert: '⚠️',
  review_requested: '📝',
  job_completed: '✅',
}

// ─── Enriched row returned by the service ───────────────────────────────────

export interface NotificationRow {
  notification: GovernanceNotification
  typedType: NotificationType
  label: string
  tone: NotificationTone
  icon: string
  /** How long ago the notification was created, in human-readable French. */
  relativeTime: string
}

// ─── Helpers ────────────────────────────────────────────────────────────────

const KNOWN_TYPES: readonly NotificationType[] = [
  'access_granted',
  'new_record',
  'delegation_granted',
  'request_status',
  'alert',
  'review_requested',
  'job_completed',
]

function isKnownType(t: string): t is NotificationType {
  return (KNOWN_TYPES as readonly string[]).includes(t)
}

/** French relative-time formatting. */
export function relativeTimeFr(createdAt: string, now: Date): string {
  const diff = now.getTime() - new Date(createdAt).getTime()
  if (diff < 0) return 'dans le futur'

  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return "à l'instant"
  if (minutes < 60) return `il y a ${minutes} min`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `il y a ${hours} h`

  const days = Math.floor(hours / 24)
  if (days < 30) return `il y a ${days} j`

  const months = Math.floor(days / 30)
  if (months < 12) return `il y a ${months} mois`

  return `il y a ${Math.floor(months / 12)} an(s)`
}

// ─── Core list builder ──────────────────────────────────────────────────────

/**
 * Build enriched, sorted notification rows.
 * Ordering: unread first, then newest first.
 */
export function notificationRows(
  notifications: GovernanceNotification[],
  now: Date = new Date(),
): NotificationRow[] {
  return notifications
    .map((n) => {
      const typedType: NotificationType = isKnownType(n.type) ? n.type : 'request_status'
      return {
        notification: n,
        typedType,
        label: NOTIFICATION_TYPE_LABELS[typedType],
        tone: NOTIFICATION_TONE[typedType],
        icon: NOTIFICATION_ICON[typedType],
        relativeTime: relativeTimeFr(n.createdAt, now),
      }
    })
    .sort((a, b) => {
      // Unread first
      if (a.notification.read !== b.notification.read) return a.notification.read ? 1 : -1
      // Then newest first
      return new Date(b.notification.createdAt).getTime() - new Date(a.notification.createdAt).getTime()
    })
}

// ─── Filtering ──────────────────────────────────────────────────────────────

export function filterNotifications(
  rows: NotificationRow[],
  filter: NotificationFilter,
): NotificationRow[] {
  if (filter === 'all') return rows
  return rows.filter((r) => r.typedType === filter)
}

export interface NotificationCounts {
  all: number
  unread: number
  access_granted: number
  new_record: number
  delegation_granted: number
  request_status: number
  alert: number
  review_requested: number
  job_completed: number
}

export function countNotifications(rows: NotificationRow[]): NotificationCounts {
  const counts: NotificationCounts = {
    all: rows.length,
    unread: 0,
    access_granted: 0,
    new_record: 0,
    delegation_granted: 0,
    request_status: 0,
    alert: 0,
    review_requested: 0,
    job_completed: 0,
  }
  for (const r of rows) {
    if (!r.notification.read) counts.unread++
    counts[r.typedType]++
  }
  return counts
}

// ─── In-memory read state (session-only, SIMULATED) ─────────────────────────

let readOverrides: Set<string> = new Set()
let listeners: Array<() => void> = []

function emitChange() {
  for (const l of listeners) l()
}

export const notificationStore = {
  /** Mark a single notification as read (SIMULATED, session-only). */
  markRead(id: string): void {
    readOverrides.add(id)
    emitChange()
  },

  /** Mark all notifications as read (SIMULATED, session-only). */
  markAllRead(notifications: GovernanceNotification[]): void {
    for (const n of notifications) readOverrides.add(n.id)
    emitChange()
  },

  /** Whether a notification has been marked as read in this session. */
  isMarkedRead(id: string): boolean {
    return readOverrides.has(id)
  },

  /** Reset to fixture state (demo reset). */
  reset(): void {
    readOverrides = new Set()
    emitChange()
  },

  subscribe(listener: () => void): () => void {
    listeners = [...listeners, listener]
    return () => {
      listeners = listeners.filter((l) => l !== listener)
    }
  },

  getSnapshot(): ReadonlySet<string> {
    return readOverrides
  },
}

/**
 * Apply session overrides to fixture notifications so that
 * mark-as-read is reflected in the UI until a demo reset.
 */
export function applyReadOverrides(notifications: GovernanceNotification[]): GovernanceNotification[] {
  return notifications.map((n) =>
    readOverrides.has(n.id) ? { ...n, read: true } : n,
  )
}
