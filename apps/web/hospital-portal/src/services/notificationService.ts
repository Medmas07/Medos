/**
 * HC-203: Notification Service client for clinician alerts.
 *
 * Calls the Notification Service (HC-202) at the configured base URL.
 * At D3, the service runs locally and the client polls the REST endpoint.
 * SSE streaming is available but the polling fallback is used for demo reliability.
 *
 * MOCK boundary: No real push broker or WebSocket. All data is fictional (HC-005).
 */

export interface AlertMetadata {
  advisory: boolean
  requires_human_review: boolean
  finding_type: string | null
}

export interface RelatedResource {
  resource_type: string
  resource_ref: string
}

export interface ClinicianAlert {
  event_id: string
  notification_id: string
  priority: 'urgent' | 'high' | 'normal' | 'low'
  title: string
  body: string
  occurred_at: string
  source: string
  alert_metadata: AlertMetadata
  related_resource: RelatedResource | null
  fictional: boolean
}

export interface ClinicianAlertsResponse {
  clinician_ref: string
  count: number
  advisory_notice: string
  alerts: ClinicianAlert[]
  fictional: boolean
}

/** Base URL for the Notification Service. Defaults to localhost for local dev. */
const NOTIFICATION_SERVICE_BASE =
  (typeof import.meta !== 'undefined' &&
    (import.meta as { env?: Record<string, string> }).env?.VITE_NOTIFICATION_SERVICE_URL) ||
  'http://localhost:8004'

/**
 * Fetch current clinician alerts from the Notification Service REST endpoint.
 * Returns MOCKED/fictional data at D3; no real clinical data is transferred.
 */
export async function fetchClinicianAlerts(
  clinicianRef: string,
): Promise<ClinicianAlertsResponse> {
  const url = `${NOTIFICATION_SERVICE_BASE}/v1/clinicians/${encodeURIComponent(clinicianRef)}/alerts`
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(8000),
  })
  if (!response.ok) {
    throw new Error(
      `Notification Service responded with ${response.status} for clinician alerts.`,
    )
  }
  return response.json() as Promise<ClinicianAlertsResponse>
}

/**
 * Returns canonical fictional demo alerts for the default demo clinician (clin-x).
 * Used as a fallback when the Notification Service is not reachable (D3 demo mode).
 */
export function getDemoClinicianAlerts(): ClinicianAlertsResponse {
  return {
    clinician_ref: 'clin-x',
    count: 3,
    advisory_notice:
      'All alerts are strictly advisory (D3). Clinician review is mandatory. ' +
      'Données fictives — aucune donnée réelle.',
    fictional: true,
    alerts: [
      {
        event_id: 'evt-notif-005',
        notification_id: 'notif-005',
        priority: 'high',
        title: 'Résultat anormal',
        body: 'HbA1c au-dessus de la plage de référence pour Karim Haddad.',
        occurred_at: '2026-09-30T16:00:00+01:00',
        source: 'canonical-fixtures',
        alert_metadata: {
          advisory: true,
          requires_human_review: true,
          finding_type: 'abnormal_lab_value',
        },
        related_resource: { resource_type: 'lab_report', resource_ref: 'alert-b-hba1c' },
        fictional: true,
      },
      {
        event_id: 'evt-alert-b-followup',
        notification_id: 'alert-b-followup',
        priority: 'normal',
        title: 'Suivi en retard',
        body: 'Contrôle prévu à 12 mois non réalisé dans les délais.',
        occurred_at: '2026-09-16T08:00:00+01:00',
        source: 'canonical-fixtures',
        alert_metadata: {
          advisory: true,
          requires_human_review: true,
          finding_type: 'missed_follow_up',
        },
        related_resource: { resource_type: 'consultation', resource_ref: 'enc-a-2025-karim' },
        fictional: true,
      },
      {
        event_id: 'evt-alert-a-external',
        notification_id: 'alert-a-external',
        priority: 'low',
        title: 'Nouvelle consultation externe',
        body: "Consultation de médecine interne à l'Hôpital Régional Oued Zitoun, avec instauration d'un traitement.",
        occurred_at: '2026-10-10T09:01:00+01:00',
        source: 'canonical-fixtures',
        alert_metadata: {
          advisory: true,
          requires_human_review: true,
          finding_type: 'new_external_consultation',
        },
        related_resource: { resource_type: 'consultation', resource_ref: 'enc-b-2026-leila' },
        fictional: true,
      },
    ],
  }
}
