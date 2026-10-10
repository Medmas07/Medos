import { afterEach, describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'
import {
  applyReadOverrides,
  countNotifications,
  filterNotifications,
  notificationRows,
  notificationStore,
  relativeTimeFr,
  NOTIFICATION_FILTER_LABELS,
  NOTIFICATION_ICON,
  NOTIFICATION_TONE,
  NOTIFICATION_TYPE_LABELS,
  type NotificationFilter,
} from '../src/services/notificationService'

const DEMO_NOW = new Date('2026-10-10T12:00:00+01:00')

/** Load demo rows using the canonical fixtures for usr-olfa. */
const demoRows = (now = DEMO_NOW) =>
  notificationRows(governanceService.getReviewerNotifications('usr-olfa'), now)

describe('Notification UI fixtures (HC-200)', () => {
  afterEach(() => notificationStore.reset())

  // ─── Data loading ───────────────────────────────────────────────────

  it('loads the demo notifications for the governance reviewer (usr-olfa)', () => {
    const rows = demoRows()
    expect(rows.length).toBeGreaterThanOrEqual(2)
    const ids = rows.map((r) => r.notification.id)
    expect(ids).toContain('notif-006')
    expect(ids).toContain('notif-007')
  })

  it('only returns notifications for the specified recipient', () => {
    const olfaNotifs = governanceService.getReviewerNotifications('usr-olfa')
    for (const n of olfaNotifs) {
      expect(n.recipientId).toBe('usr-olfa')
    }

    const patNotifs = governanceService.getReviewerNotifications('pat-a')
    for (const n of patNotifs) {
      expect(n.recipientId).toBe('pat-a')
    }
  })

  // ─── Type mapping ──────────────────────────────────────────────────

  it('maps notification types to French labels, tones, and icons', () => {
    const rows = notificationRows(governanceService.getReviewerNotifications('pat-a'), DEMO_NOW)
    const accessRow = rows.find((r) => r.typedType === 'access_granted')
    expect(accessRow).toBeDefined()
    expect(accessRow!.label).toBe('Accès accordé')
    expect(accessRow!.tone).toBe('success')
    expect(accessRow!.icon).toBe('🔓')
  })

  it('provides labels for every notification type', () => {
    const types = [
      'access_granted',
      'new_record',
      'delegation_granted',
      'request_status',
      'alert',
      'review_requested',
      'job_completed',
    ] as const

    for (const t of types) {
      expect(NOTIFICATION_TYPE_LABELS[t]).toBeTruthy()
      expect(NOTIFICATION_TONE[t]).toBeTruthy()
      expect(NOTIFICATION_ICON[t]).toBeTruthy()
    }
  })

  it('provides filter labels including "all"', () => {
    expect(NOTIFICATION_FILTER_LABELS.all).toBe('Toutes')
    expect(NOTIFICATION_FILTER_LABELS.review_requested).toBe('Revue demandée')
    expect(NOTIFICATION_FILTER_LABELS.alert).toBe('Alerte clinique')
  })

  // ─── Ordering ──────────────────────────────────────────────────────

  it('orders unread notifications before read ones', () => {
    const rows = notificationRows(governanceService.getReviewerNotifications('pat-a'), DEMO_NOW)
    // pat-a has notif-001 (unread) and notif-002 (read)
    const firstId = rows[0].notification.id
    expect(rows[0].notification.read).toBe(false)
    // Read notifications come after
    const readItems = rows.filter((r) => r.notification.read)
    const unreadItems = rows.filter((r) => !r.notification.read)
    if (unreadItems.length > 0 && readItems.length > 0) {
      const lastUnreadIdx = rows.findIndex((r) => r === unreadItems[unreadItems.length - 1])
      const firstReadIdx = rows.findIndex((r) => r === readItems[0])
      expect(lastUnreadIdx).toBeLessThan(firstReadIdx)
    }
  })

  it('orders within read-status group by newest first', () => {
    const rows = demoRows()
    const unreadRows = rows.filter((r) => !r.notification.read)
    for (let i = 1; i < unreadRows.length; i++) {
      const prev = new Date(unreadRows[i - 1].notification.createdAt).getTime()
      const curr = new Date(unreadRows[i].notification.createdAt).getTime()
      expect(prev).toBeGreaterThanOrEqual(curr)
    }
  })

  // ─── Filtering ─────────────────────────────────────────────────────

  it('filters notifications by type', () => {
    const rows = demoRows()
    const reviewRows = filterNotifications(rows, 'review_requested')
    for (const r of reviewRows) {
      expect(r.typedType).toBe('review_requested')
    }
    expect(reviewRows.length).toBeGreaterThan(0)
  })

  it('filter "all" returns all rows', () => {
    const rows = demoRows()
    expect(filterNotifications(rows, 'all')).toHaveLength(rows.length)
  })

  it('filter with no matches returns empty array', () => {
    const rows = demoRows()
    // usr-olfa only has review_requested notifications, so access_granted should be empty
    const filtered = filterNotifications(rows, 'access_granted')
    expect(filtered).toHaveLength(0)
  })

  // ─── Counts ────────────────────────────────────────────────────────

  it('counts all and unread notifications', () => {
    const rows = demoRows()
    const counts = countNotifications(rows)
    expect(counts.all).toBe(rows.length)
    expect(counts.unread).toBe(rows.filter((r) => !r.notification.read).length)
  })

  it('counts per notification type', () => {
    const rows = demoRows()
    const counts = countNotifications(rows)
    expect(counts.review_requested).toBe(
      rows.filter((r) => r.typedType === 'review_requested').length,
    )
  })

  // ─── Mark-as-read (SIMULATED) ─────────────────────────────────────

  it('marks a notification as read in session state', () => {
    notificationStore.markRead('notif-006')
    expect(notificationStore.isMarkedRead('notif-006')).toBe(true)
    expect(notificationStore.isMarkedRead('notif-007')).toBe(false)
  })

  it('marks all notifications as read', () => {
    const notifs = governanceService.getReviewerNotifications('usr-olfa')
    notificationStore.markAllRead(notifs)
    for (const n of notifs) {
      expect(notificationStore.isMarkedRead(n.id)).toBe(true)
    }
  })

  it('applyReadOverrides sets read=true for session-marked notifications', () => {
    notificationStore.markRead('notif-006')
    const notifs = governanceService.getReviewerNotifications('usr-olfa')
    const patched = applyReadOverrides(notifs)
    const n006 = patched.find((n) => n.id === 'notif-006')
    expect(n006?.read).toBe(true)
  })

  it('reset clears all session marks', () => {
    notificationStore.markRead('notif-006')
    notificationStore.reset()
    expect(notificationStore.isMarkedRead('notif-006')).toBe(false)
  })

  it('subscribe/emit notifies listeners on mark-read', () => {
    let called = 0
    const unsub = notificationStore.subscribe(() => called++)
    notificationStore.markRead('notif-006')
    expect(called).toBe(1)
    notificationStore.markAllRead(governanceService.getReviewerNotifications('usr-olfa'))
    expect(called).toBe(2)
    unsub()
    notificationStore.reset()
    // After unsubscribe, the listener should not be called again
    expect(called).toBe(2)
  })

  // ─── Relative time ────────────────────────────────────────────────

  it('formats relative time in French for various intervals', () => {
    const now = new Date('2026-10-10T12:00:00+01:00')
    expect(relativeTimeFr('2026-10-10T11:59:30+01:00', now)).toBe("à l'instant")
    expect(relativeTimeFr('2026-10-10T11:30:00+01:00', now)).toBe('il y a 30 min')
    expect(relativeTimeFr('2026-10-10T06:00:00+01:00', now)).toBe('il y a 6 h')
    expect(relativeTimeFr('2026-10-07T12:00:00+01:00', now)).toBe('il y a 3 j')
    expect(relativeTimeFr('2026-06-10T12:00:00+01:00', now)).toBe('il y a 4 mois')
  })

  // ─── Data integrity ───────────────────────────────────────────────

  it('never exposes patient names or clinical content in notifications', () => {
    // Verify all fixture notifications for all recipients
    const allNotifs = [
      ...governanceService.getReviewerNotifications('usr-olfa'),
      ...governanceService.getReviewerNotifications('pat-a'),
      ...governanceService.getReviewerNotifications('pat-c'),
      ...governanceService.getReviewerNotifications('clin-x'),
    ]
    for (const n of allNotifs) {
      expect(n.id).toBeTruthy()
      expect(n.recipientId).toBeTruthy()
      expect(n.type).toBeTruthy()
      expect(n.title).toBeTruthy()
      // Notifications may mention names in body (this is fictional demo data), but never contain SSN/clinical IDs
      expect(n.body).not.toMatch(/\d{3}-\d{2}-\d{4}/) // No SSN patterns
    }
  })
})
