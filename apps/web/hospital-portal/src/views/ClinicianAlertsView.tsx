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

const PRIORITY_TONE = {
  urgent: 'critical',
  high: 'warning',
  normal: 'info',
  low: 'neutral',
} as const

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
  const tone = PRIORITY_TONE[alert.priority] ?? 'neutral'
  return (
    <div
      id={`clinician-alert-${alert.notification_id}`}
      style={{
        borderLeft: `4px solid var(--color-${
          tone === 'critical'
            ? 'red-500'
            : tone === 'warning'
              ? 'amber-400'
              : tone === 'info'
                ? 'blue-400'
                : 'slate-300'
        })`,
        padding: '0.75rem 1rem',
        marginBottom: '0.75rem',
        background: 'var(--color-white, #fff)',
        borderRadius: '0 0.375rem 0.375rem 0',
        boxShadow: '0 1px 3px rgba(0,0,0,.06)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
        <p style={{ fontWeight: 600, color: 'var(--color-slate-900, #0f172a)', margin: 0 }}>
          {alert.title}
        </p>
        <Badge tone={tone as 'critical' | 'warning' | 'info' | 'neutral'}>
          {PRIORITY_LABEL[alert.priority]}
        </Badge>
      </div>
      <p style={{ color: 'var(--color-slate-700, #334155)', margin: '0.25rem 0 0' }}>
        {alert.body}
      </p>
      {alert.alert_metadata.finding_type && (
        <p style={{ fontSize: '0.75rem', color: 'var(--color-slate-500, #64748b)', marginTop: '0.25rem' }}>
          Type : {alert.alert_metadata.finding_type.replace(/_/g, ' ')}
        </p>
      )}
      <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--color-slate-400, #94a3b8)' }}>
        <span>{formatDateTime(alert.occurred_at)}</span>
        {alert.related_resource && (
          <span>Réf : {alert.related_resource.resource_ref}</span>
        )}
        {alert.alert_metadata.advisory && (
          <span style={{ color: 'var(--color-amber-600, #d97706)', fontWeight: 500 }}>
            ⚠ Consultatif — revue clinicien requise
          </span>
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
        <LoadingState label="Chargement des alertes clinicien…" />
      ) : (
        <div style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: '1fr' }}>
          {/* Summary cards */}
          <div
            style={{
              display: 'grid',
              gap: '1rem',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            }}
          >
            <Card
              title="Total alertes"
              actions={
                isFallback ? <DemoBadge>Simulé</DemoBadge> : <DemoBadge>Fictif</DemoBadge>
              }
            >
              <p
                id="clinician-alert-count"
                style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-slate-900, #0f172a)', margin: 0 }}
              >
                {alerts.length}
              </p>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-slate-500)', marginTop: 4 }}>
                {lastRefreshed
                  ? `Actualisé ${formatDateTime(lastRefreshed.toISOString())}`
                  : '—'}
              </p>
            </Card>
            <Card title="Urgentes / Élevées" actions={<DemoBadge>Fictif</DemoBadge>}>
              <p
                style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-red-600, #dc2626)', margin: 0 }}
              >
                {alerts.filter((a) => a.priority === 'urgent' || a.priority === 'high').length}
              </p>
            </Card>
            <Card title="Mode actualisation" actions={<DemoBadge>D3</DemoBadge>}>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-slate-700)', margin: 0 }}>
                Polling {POLL_INTERVAL_MS / 1000}s
              </p>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-slate-500)', marginTop: 4 }}>
                Non broker-backed (D3)
              </p>
            </Card>
          </div>

          {/* Alert list */}
          <Card
            id="clinician-alerts-list-card"
            title="File de priorité — alertes cliniques"
            description={`Clinicien : ${DEMO_CLINICIAN_REF} · Triées par priorité puis date · Toutes consultatives`}
          >
            {alerts.length === 0 ? (
              <EmptyState
                title="Aucune alerte"
                description="Aucune alerte clinique en attente pour ce clinicien."
              />
            ) : (
              <div style={{ marginTop: '0.5rem' }}>
                {alerts.map((alert) => (
                  <AlertCard key={alert.event_id} alert={alert} />
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </>
  )
}
