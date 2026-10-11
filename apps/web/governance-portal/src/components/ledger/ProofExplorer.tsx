import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  type Tone,
} from '@hackcure/design-system'
import { timelineEntry } from '../../services/auditTimeline'
import { governanceService } from '../../services/governanceService'
import {
  ALLOWED_PROOF_FIELDS,
  PROOF_STATE_LABELS,
  countByState,
  verifyProofs,
  type ProofState,
  type ProofVerification,
} from '../../services/proofExplorer'

const STATE_TONES: Record<ProofState, Tone> = {
  verified: 'success',
  tampered: 'danger',
  inconsistent: 'warning',
}

const formatDateTime = (iso: string) =>
  new Date(iso).toLocaleString('fr-TN', { dateStyle: 'medium', timeStyle: 'medium', hourCycle: 'h23' })

type Status = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; results: ProofVerification[] }

interface ProofExplorerProps {
  onInspectProof?: (proofId: string) => void
}

const eventFor = (id: string) => governanceService.getAuditEvents().find((e) => e.id === id)

function eventTitle(eventId: string): string {
  const event = eventFor(eventId)
  if (!event) return 'Événement introuvable'
  return timelineEntry(event, {
    decision: (id) => governanceService.getDecision(id),
    proofForEvent: (id) => governanceService.getProofForEvent(id),
  }).title
}

const orgNames = (ids: readonly string[]) =>
  ids.map((id) => governanceService.getOrganization(id)?.shortName ?? id)

/** MOCKED BLOCKCHAIN explorer: each simulated proof, verified again in the browser (HC-080). */
export function ProofExplorer({ onInspectProof }: ProofExplorerProps) {
  // Web Crypto exists only in secure contexts (HTTPS or localhost).
  const [status, setStatus] = useState<Status>(() =>
    globalThis.crypto?.subtle
      ? { kind: 'loading' }
      : { kind: 'error', message: 'Web Crypto est indisponible : ouvrez le portail en HTTPS ou sur localhost.' },
  )
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    if (!globalThis.crypto?.subtle) return
    let cancelled = false
    verifyProofs(governanceService.getLedgerProofs(), eventFor)
      .then((results) => {
        if (!cancelled) setStatus({ kind: 'ready', results })
      })
      .catch((error: unknown) => {
        if (!cancelled) setStatus({ kind: 'error', message: String(error) })
      })
    return () => {
      cancelled = true
    }
  }, [])

  const header = (
    <div className="space-y-3">
      <Alert tone="demo" title="MOCKED BLOCKCHAIN — registre local simulé">
        Aucune chaîne, aucun réseau, aucun consensus ni ancrage réel : les preuves sont des données de démonstration fictives. Le portail recalcule seulement chaque empreinte SHA-256 dans le navigateur et vérifie que la preuve n'ancre que des métadonnées de gouvernance minimisées. Le port de registre et un registre simulé ou réel sont planifiés (HC-190 à HC-194).
      </Alert>
    </div>
  )

  if (status.kind === 'loading') {
    return (
      <Card title="Explorateur de Preuves de Registre" actions={<DemoBadge>MOCKED BLOCKCHAIN</DemoBadge>}>
        {header}
        <LoadingState label="Vérification des preuves en cours…" />
      </Card>
    )
  }
  if (status.kind === 'error') {
    return (
      <Card title="Explorateur de Preuves de Registre" actions={<DemoBadge>MOCKED BLOCKCHAIN</DemoBadge>}>
        {header}
        <ErrorState title="Vérification impossible" description={status.message} />
      </Card>
    )
  }

  const { results } = status
  const counts = countByState(results)
  const selected = results.find((r) => r.proof.id === selectedId) ?? results[0]

  return (
    <Card title="Explorateur de Preuves de Registre" actions={<DemoBadge>MOCKED BLOCKCHAIN</DemoBadge>}>
      <div className="space-y-4">
        {header}

        {results.length === 0 ? (
          <EmptyState
            title="Aucune preuve ancrée"
            description="Aucune décision n'a encore de preuve dans le registre simulé."
          />
        ) : (
          <>
            <p className="text-xs text-slate-600" aria-live="polite">
              {results.length} preuve(s) recalculée(s) : {counts.verified} vérifiée(s), {counts.tampered} altérée(s),{' '}
              {counts.inconsistent} incohérente(s).
            </p>

            <ul className="space-y-2" aria-label="Preuves du registre simulé">
              {results.map((r) => {
                const isSelected = r.proof.id === selected?.proof.id
                return (
                  <li key={r.proof.id}>
                    <button
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => setSelectedId(r.proof.id)}
                      className={`grid w-full grid-cols-1 gap-2 rounded-xl border p-3 text-left text-xs transition-colors sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_auto] sm:items-center ${
                        isSelected ? 'border-brand-600 bg-brand-50' : 'border-slate-200 bg-surface hover:bg-brand-50/60'
                      }`}
                    >
                      <span className="min-w-0">
                        <span className="block font-semibold text-slate-900">{eventTitle(r.proof.auditEventId)}</span>
                        <span className="block font-mono text-slate-500">
                          {r.proof.id} • {r.proof.auditEventId}
                        </span>
                        <span className="block truncate font-mono text-[11px] text-slate-600" title={r.proof.hash}>
                          {r.proof.hash}
                        </span>
                      </span>
                      <span className="min-w-0 text-slate-600">
                        <span className="block">{orgNames(r.proof.anchoredPayload.organizationIds).join(', ')}</span>
                        <span className="block text-slate-500">Ancrée le {formatDateTime(r.proof.anchoredAt)}</span>
                      </span>
                      <span className="flex flex-wrap items-center gap-1.5 sm:justify-end">
                        <Badge tone={STATE_TONES[r.state]} dot>
                          {PROOF_STATE_LABELS[r.state]}
                        </Badge>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>

            {selected && <ProofDetail result={selected} onInspectProof={onInspectProof} />}
          </>
        )}
      </div>
    </Card>
  )
}

function ProofDetail({
  result,
  onInspectProof,
}: {
  result: ProofVerification
  onInspectProof?: (proofId: string) => void
}) {
  const { proof } = result
  const checks: { label: string; ok: boolean; detail: string }[] = [
    {
      label: 'Empreinte recalculée',
      ok: result.hashMatches,
      detail: result.hashMatches
        ? 'Le SHA-256 du payload canonique concorde avec l’empreinte enregistrée.'
        : 'Le SHA-256 du payload canonique ne concorde pas : la preuve ou la décision a été modifiée.',
    },
    {
      label: 'Événement d’audit lié',
      ok: result.eventLinked,
      detail: result.eventLinked
        ? `Le payload désigne ${proof.auditEventId}, présent dans la piste d’audit.`
        : `Le payload ne désigne pas ${proof.auditEventId}, ou cet événement est introuvable.`,
    },
    {
      label: 'Payload minimisé',
      ok: result.forbiddenFields.length === 0,
      detail:
        result.forbiddenFields.length === 0
          ? `Uniquement des champs autorisés : ${ALLOWED_PROOF_FIELDS.join(', ')}.`
          : `Champs interdits ancrés : ${result.forbiddenFields.join(', ')}.`,
    },
  ]
  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-slate-900">
          {proof.id} — {eventTitle(proof.auditEventId)}
        </span>
        <Badge tone={STATE_TONES[result.state]} dot>
          {PROOF_STATE_LABELS[result.state]}
        </Badge>
      </div>

      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Type d’événement</dt>
          <dd className="text-slate-800">{eventTitle(proof.auditEventId)} ({proof.anchoredPayload.decisionId})</dd>
        </div>
        <div>
          <dt className="text-slate-500">Organisations</dt>
          <dd className="text-slate-800">{orgNames(proof.anchoredPayload.organizationIds).join(', ')}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Ancrée le</dt>
          <dd className="text-slate-800">{formatDateTime(proof.anchoredAt)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Registre</dt>
          <dd className="font-mono text-slate-800">
            {proof.ledger} ({proof.hashAlgorithm}){proof.simulated && ' — simulé'}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Empreinte enregistrée</dt>
          <dd className="break-all font-mono text-slate-800">{proof.hash}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Empreinte recalculée dans le navigateur</dt>
          <dd className={`break-all font-mono ${result.hashMatches ? 'text-success-700' : 'text-danger-700'}`}>
            {result.recomputedHash}
          </dd>
        </div>
      </dl>

      <ul className="space-y-1.5" aria-label="Contrôles de la preuve">
        {checks.map((c) => (
          <li key={c.label} className="flex gap-2">
            <Badge tone={c.ok ? 'success' : 'danger'} dot>
              {c.ok ? 'Conforme' : 'Non conforme'}
            </Badge>
            <span>
              <span className="font-medium text-slate-800">{c.label} : </span>
              <span className="text-slate-600">{c.detail}</span>
            </span>
          </li>
        ))}
      </ul>

      {result.claimDisagrees && (
        <Alert tone="warning" title="Statut déclaré contredit">
          La preuve se déclare « {proof.verificationStatus} », mais le recalcul donne « {PROOF_STATE_LABELS[result.state]} ». Seul le recalcul fait foi.
        </Alert>
      )}

      <div>
        <div className="font-medium text-slate-700">Payload ancré (métadonnées minimisées, jamais de donnée médicale)</div>
        <pre className="mt-1 overflow-x-auto rounded border border-slate-200 bg-surface p-3 font-mono text-slate-800">
          {JSON.stringify(proof.anchoredPayload, null, 2)}
        </pre>
      </div>

      {onInspectProof && (
        <Button size="sm" variant="secondary" onClick={() => onInspectProof(proof.id)}>
          Tester une altération dans le vérificateur
        </Button>
      )}
    </div>
  )
}
