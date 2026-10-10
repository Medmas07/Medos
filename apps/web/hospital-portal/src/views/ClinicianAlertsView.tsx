/**
 * HC-203: Real-time clinician alerts view (D3).
 *
 * Polls the Notification Service for advisory clinical alerts addressed to the
 * demo clinician (clin-x). Falls back to canonical fictional demo data when the
 * service is unreachable.
 *
 * D3 boundary:
 *  - Polling-based refresh (every 15 s), not a live WebSocket or broker push.
 *  - All data is fictional (HC-005). No real patient data is shown.
 *  - All alerts are advisory; no clinical action should be taken without human review.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  LoadingState,
  PageHeader,
  StatCard,
  type Tone,
} from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import {
  fetchClinicianAlerts,
  getDemoClinicianAlerts,
  type ClinicianAlert,
  type ClinicianAlertsResponse,
} from '../services/notificationService'

/** Demo clinician used across the HC-005 canonical fixtures. */
const DEMO_CLINICIAN_REF = 'clin-x'
/** Poll interval in milliseconds. */
const POLL_INTERVAL_MS = 15_000

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string; data: ClinicianAlertsResponse }
  | { kind: 'ready'; data: ClinicianAlertsResponse; source: 'service' | 'demo' }

const PRIORITY_TONE: Record<ClinicianAlert['priority'], Tone> = {
  urgent: 'danger',
  high: 'warning',
  normal: 'info',
  low: 'neutral',
}

const PRIORITY_BORDER: Record<ClinicianAlert['priority'], string> = {
  urgent: 'border-l-danger-600',
  high: 'border-l-warning-600',
  normal: 'border-l-info-600',
  low: 'border-l-line-strong',
}

const PRIORITY_LABEL: Record<ClinicianAlert['priority'], string> = {
  urgent: 'Urgent',
  high: 'Élevé',
  normal: 'Normal',
  low: 'Faible',
}

const PRIORITY_ORDER: Record<ClinicianAlert['priority'], number> = {
  urgent: 0,
  high: 1,
  normal: 2,
  low: 3,
}

function sortAlerts(alerts: ClinicianAlert[]): ClinicianAlert[] {
  return [...alerts].sort(
    (a, b) =>
      PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] ||
      new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime(),
  )
}

function AlertCard({ alert }: { alert: ClinicianAlert }) {
  return (
    <div
      id={`clinician-alert-${alert.notification_id}`}
      className={`rounded-xl border border-l-4 border-line bg-surface px-4 py-3 shadow-card ${PRIORITY_BORDER[alert.priority]}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold text-ink">{alert.title}</p>
        <Badge tone={PRIORITY_TONE[alert.priority]}>{PRIORITY_LABEL[alert.priority]}</Badge>
      </div>
      <p className="mt-1 text-ink-soft">{alert.body}</p>
      {alert.alert_metadata.finding_type && (
        <p className="mt-1 text-xs text-ink-muted">
          Type : {alert.alert_metadata.finding_type.replace(/_/g, ' ')}
        </p>
      )}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
        <span className="tabular">{formatDateTime(alert.occurred_at)}</span>
        {alert.related_resource && <span>Réf : {alert.related_resource.resource_ref}</span>}
        {alert.alert_metadata.advisory && (
          <span className="font-medium text-warning-700">⚠ Consultatif — revue clinicien requise</span>
        )}
      </div>
    </div>
  )
}

export function ClinicianAlertsView() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = useCallback(async (silent = false) => {
    if (!silent) setState({ kind: 'loading' })
    setIsRefreshing(true)
    try {
      const data = await fetchClinicianAlerts(DEMO_CLINICIAN_REF)
      setState({ kind: 'ready', data, source: 'service' })
      setLastRefreshed(new Date())
    } catch {
      // Service unreachable — fall back to canonical fictional demo data
      const demo = getDemoClinicianAlerts()
      setState({ kind: 'error', message: 'Service de notifications inaccessible — données fictives de démonstration.', data: demo })
      setLastRefreshed(new Date())
    } finally {
      setIsRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void load()
    timerRef.current = setInterval(() => void load(true), POLL_INTERVAL_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [load])

  const alerts =
    state.kind === 'loading'
      ? []
      : sortAlerts(state.kind === 'ready' ? state.data.alerts : state.data.alerts)

  const isFallback = state.kind === 'error'

  return (
    <>
      <PageHeader
        eyebrow="HC-203 · Intégration temps réel"
        title="Alertes clinicien"
        description="Alertes cliniques consultatives transmises par le Service de Notifications (HC-202). Toutes les données sont fictives (HC-005). Aucune action clinique ne doit être prise sans revue humaine."
        actions={
          <Button
            id="clinician-alerts-refresh-btn"
            variant="secondary"
            onClick={() => void load(true)}
            disabled={isRefreshing}
          >
            {isRefreshing ? 'Actualisation…' : 'Actualiser'}
          </Button>
        }
      />

      {/* Advisory safety banner — always shown */}
      <Alert tone="warning" title="Données consultatives uniquement (D3)" className="mb-4">
        Ces alertes sont générées automatiquement à titre <strong>consultatif uniquement</strong>. 
        Toute action clinique doit faire l'objet d'une revue par un clinicien habilité. 
        L'IA et le système de priorité ne constituent pas une autorité clinique autonome.
      </Alert>

      {isFallback && (
        <Alert tone="info" title="Service non joignable — mode démo" className="mb-4">
          {(state as { message: string }).message}
        </Alert>
      )}

      {state.kind === 'loading' ? (
        <LoadingState variant="skeleton" label="Chargement des alertes clinicien…" />
      ) : (
        <div className="grid gap-6">
          {/* Summary cards */}
          <div className="hc-stagger grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div id="clinician-alert-count">
              <StatCard
                label="Total alertes"
                value={alerts.length}
                hint={lastRefreshed ? `Actualisé ${formatDateTime(lastRefreshed.toISOString())}` : '—'}
                badge={isFallback ? <DemoBadge>Simulé</DemoBadge> : <DemoBadge>Fictif</DemoBadge>}
                className="h-full"
              />
            </div>
            <StatCard
              label="Urgentes / Élevées"
              value={alerts.filter((a) => a.priority === 'urgent' || a.priority === 'high').length}
              badge={<DemoBadge>Fictif</DemoBadge>}
            />
            <StatCard
              label="Mode actualisation"
              value={`${POLL_INTERVAL_MS / 1000} s`}
              hint="Polling · non broker-backed (D3)"
              badge={<DemoBadge>D3</DemoBadge>}
            />
          </div>

          {/* Alert list */}
          <div id="clinician-alerts-list-card">
          <Card
            title="File de priorité — alertes cliniques"
            description={`Clinicien : ${DEMO_CLINICIAN_REF} · Triées par priorité puis date · Toutes consultatives`}
          >
            {alerts.length === 0 ? (
              <EmptyState
                title="Aucune alerte"
                description="Aucune alerte clinique en attente pour ce clinicien."
              />
            ) : (
              <div className="hc-stagger space-y-3">
                {alerts.map((alert) => (
                  <AlertCard key={alert.event_id} alert={alert} />
                ))}
              </div>
            )}
          </Card>
          </div>
        </div>
      )}
    </>
  )
}
