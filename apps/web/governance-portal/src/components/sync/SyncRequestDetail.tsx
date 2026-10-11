import {
  Alert,
  Badge,
  Card,
  DemoBadge,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'
import type { SynchronizationRequest } from '../../types/governance'

const SCOPE_DEFINITIONS: Record<string, { label: string; description: string }> = {
  medications: {
    label: 'Traitements & Prescriptions',
    description: 'Historique des ordonnances, posologies actives et alertes médicamenteuses',
  },
  labReports: {
    label: 'Résultats de Laboratoire',
    description: 'Bilans sanguins, biochimie et rapports d’analyses biologiques',
  },
  encounters: {
    label: 'Consultations & Passages',
    description: 'Comptes-rendus d’admissions, urgences et consultations spécialisées',
  },
}

interface SyncRequestDetailProps {
  request: SynchronizationRequest
  reviewForm?: React.ReactNode
}

export function SyncRequestDetail({ request, reviewForm }: SyncRequestDetailProps) {
  const reqOrg = governanceService.getOrganization(request.requesterOrganizationId)
  const tgtOrg = governanceService.getOrganization(request.targetOrganizationId)
  const patient = governanceService.getPatient(request.patientId)
  const grant = governanceService.getAccessGrant(request.consent.accessGrantId)
  const granteeClinician = grant ? governanceService.getPerson(grant.granteeId) : undefined
  const decision = governanceService.getDecision(request.decisionId)
  const auditEvent = decision
    ? governanceService.getAuditEvents().find((e) => e.subjectId === decision.id)
    : undefined
  const proof = auditEvent ? governanceService.getProofForEvent(auditEvent.id) : undefined

  const requesterLocalId = patient?.localIdentifiers?.find(
    (li) => li.organizationId === request.requesterOrganizationId
  )?.value

  const targetLocalId = patient?.localIdentifiers?.find(
    (li) => li.organizationId === request.targetOrganizationId
  )?.value

  // Scope compliance verification against patient grant (if grant-based)
  const grantScopeMismatch =
    request.consent.basis === 'patient_grant' && grant
      ? request.scope.filter((s) => !grant.scope.includes(s))
      : []

  const formattedSubmittedAt = new Date(request.submittedAt).toLocaleDateString('fr-TN', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <Card
      title={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-900">Dossier de Synchronisation</span>
            <span className="font-mono text-sm text-slate-500">#{request.id}</span>
          </div>
          <div className="flex items-center gap-2">
            {request.status === 'pending' && (
              <Badge tone="warning" dot>
                En cours d'instruction
              </Badge>
            )}
            {request.status === 'approved' && (
              <Badge tone="success" dot>
                Synchronisation Approuvée
              </Badge>
            )}
            {request.status === 'rejected' && (
              <Badge tone="danger" dot>
                Synchronisation Rejetée
              </Badge>
            )}
            <DemoBadge>D1 — Fictif</DemoBadge>
          </div>
        </div>
      }
      className="space-y-6"
    >
      {/* 1. Finalité déclarée */}
      <section className="space-y-2 border-b border-slate-100 pb-4">
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500">
          <span>1. Finalité Clinique Déclarée</span>
          <span className="font-normal lowercase text-slate-400">soumis le {formattedSubmittedAt}</span>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-sm font-medium text-slate-900">« {request.purpose} »</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="font-medium text-slate-700">Classification :</span>
            <Badge tone="info">Continuité des soins directs</Badge>
            <span className="text-slate-400">•</span>
            <span>Contrôle de conformité éthique requis avant ouverture de flux</span>
          </div>
        </div>
      </section>

      {/* 2. Établissements Source & Cible */}
      <section className="space-y-3 border-b border-slate-100 pb-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          2. Établissements Partenaires (Source & Cible)
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {/* Établissement demandeur (source de la requête) */}
          <div className="rounded-xl border border-slate-200 bg-surface p-3 shadow-card">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-500">Établissement Demandeur</span>
              <Badge tone="neutral">Consommateur du flux</Badge>
            </div>
            <div className="mt-1 font-semibold text-slate-900">{reqOrg?.name ?? request.requesterOrganizationId}</div>
            <div className="text-xs text-slate-500">{reqOrg?.city ?? 'Tunisie'}</div>

            <div className="mt-2.5 space-y-1.5 border-t border-slate-100 pt-2 text-xs text-slate-600">
              <div className="flex items-center justify-between">
                <span>État du nœud :</span>
                {reqOrg?.node?.status === 'online' ? (
                  <Badge tone="success" dot>En ligne ({reqOrg.node.version})</Badge>
                ) : (
                  <Badge tone="warning">Dégradé</Badge>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span>Adaptateur DMI :</span>
                <span className="font-mono text-slate-700">{reqOrg?.node?.dmiState ?? 'dmi-local'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>IPP local patient :</span>
                <span className="font-mono font-medium text-slate-800">{requesterLocalId ?? 'Non rattaché'}</span>
              </div>
            </div>
          </div>

          {/* Établissement cible (détenteur des données sources) */}
          <div className="rounded-xl border border-slate-200 bg-surface p-3 shadow-card">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-500">Détenteur des Données</span>
              <Badge tone="info">Hôpital Cible</Badge>
            </div>
            <div className="mt-1 font-semibold text-slate-900">{tgtOrg?.name ?? request.targetOrganizationId}</div>
            <div className="text-xs text-slate-500">{tgtOrg?.city ?? 'Tunisie'}</div>

            <div className="mt-2.5 space-y-1.5 border-t border-slate-100 pt-2 text-xs text-slate-600">
              <div className="flex items-center justify-between">
                <span>État du nœud :</span>
                {tgtOrg?.node?.status === 'online' ? (
                  <Badge tone="success" dot>En ligne ({tgtOrg.node.version})</Badge>
                ) : (
                  <Badge tone="warning">Dégradé</Badge>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span>Adaptateur DMI :</span>
                <span className="font-mono text-slate-700">{tgtOrg?.node?.dmiState ?? 'dmi-local'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>IPP local patient :</span>
                <span className="font-mono font-medium text-slate-800">{targetLocalId ?? 'Non rattaché'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded bg-info-50 p-2 text-xs text-info-800">
          <span className="font-semibold">Invariant d'architecture :</span> Les données médicales restent sous la garde exclusive du nœud de l’établissement cible ({tgtOrg?.shortName ?? 'Cible'}). Aucun transfert massif ni stockage centralisé n’est effectué.
        </div>
      </section>

      {/* 3. Patient & Périmètre de Données */}
      <section className="space-y-3 border-b border-slate-100 pb-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          3. Identité du Patient & Périmètre Clinique Autorisé
        </div>

        {patient ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <span className="text-sm font-semibold text-slate-900">
                  {patient.firstName} {patient.lastName}
                </span>
                <span className="ml-2 font-mono text-xs text-slate-500">({patient.federatedId})</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-600">
                {patient.birthDate && <span>Né(e) le {patient.birthDate}</span>}
                {patient.city && <span>• {patient.city}</span>}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500">Identifiant patient : {request.patientId}</div>
        )}

        <div className="space-y-2">
          <div className="text-xs font-medium text-slate-700">
            Catégories de données demandées ({request.scope.length}) :
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {request.scope.map((scopeKey) => {
              const def = SCOPE_DEFINITIONS[scopeKey]
              return (
                <div
                  key={scopeKey}
                  className="rounded-xl border border-slate-200 bg-surface p-2 text-xs shadow-card"
                >
                  <div className="flex items-center gap-2">
                    <Badge tone="neutral">{scopeKey}</Badge>
                    <span className="font-semibold text-slate-800">{def?.label ?? scopeKey}</span>
                  </div>
                  {def?.description && (
                    <p className="mt-1 text-[11px] text-slate-500">{def.description}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* 4. Durée & Validité Temporelle */}
      <section className="space-y-2 border-b border-slate-100 pb-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          4. Durée & Fenêtre Temporelle d'Accès
        </div>
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-surface p-3 text-xs">
          <div>
            <div className="text-slate-500">Durée demandée :</div>
            <div className="text-sm font-semibold text-slate-900">
              {request.durationDays} jours consécutifs
            </div>
          </div>
          <div>
            <div className="text-slate-500">Principe de limitation de conservation :</div>
            <div className="font-medium text-slate-700">
              {request.durationDays <= 30 && 'Durée proportionnée à l’épisode de soins (≤ 30 j)'}
              {request.durationDays > 30 && request.durationDays <= 90 && 'Durée trimestrielle pour suivi post-urgences (≤ 90 j)'}
              {request.durationDays > 90 && 'Durée prolongée nécessitant justification médicale stricte'}
            </div>
          </div>
        </div>
      </section>

      {/* 5. Base de Consentement & Décision d'Arbitrage */}
      <section className="space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          5. Base de Consentement & Décision de l’Autorité
        </div>

        {/* État du consentement */}
        <div className="rounded-xl border border-slate-200 bg-surface p-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-700">Régime d'autorisation légale :</span>
            <Badge
              tone={
                request.consent.basis === 'patient_grant'
                  ? 'success'
                  : request.consent.basis === 'signed_consent_form'
                    ? 'info'
                    : 'danger'
              }
            >
              {request.consent.basis === 'patient_grant' && 'Autorisation patiente active (Portail Patient)'}
              {request.consent.basis === 'signed_consent_form' && 'Formulaire écrit de consentement signé'}
              {request.consent.basis === 'none' && 'Aucun consentement patient fourni'}
            </Badge>
          </div>

          {request.consent.basis === 'patient_grant' && grant && (
            <div className="mt-3 space-y-1.5 rounded border border-success-100 bg-success-50/60 p-2 text-slate-700">
              <div className="flex items-center justify-between">
                <span className="font-medium">Jeton de consentement patient :</span>
                <span className="font-mono text-success-800">{grant.id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Médecin bénéficiaire désigné :</span>
                <span className="font-semibold text-slate-800">
                  {granteeClinician ? `${granteeClinician.title ?? 'Dr'} ${granteeClinician.firstName} ${granteeClinician.lastName}` : grant.granteeId}
                  {granteeClinician?.specialty ? ` (${granteeClinician.specialty})` : ''}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Validité de l'accord patient :</span>
                <span>Jusqu'au {new Date(grant.expiresAt).toLocaleDateString('fr-TN')}</span>
              </div>
              {grantScopeMismatch.length > 0 ? (
                <div className="mt-1 font-semibold text-warning-700">
                  Attention : périmètre hors mandat ({grantScopeMismatch.join(', ')})
                </div>
              ) : (
                <div className="mt-1 text-[11px] text-success-700">
                  ✓ Le périmètre demandé est intégralement couvert par l'accord actif de la patiente.
                </div>
              )}
            </div>
          )}

          {request.consent.basis === 'signed_consent_form' && (
            <div className="mt-2 text-slate-600">
              Document papier signé lors de l'admission aux urgences, numérisé et conservé sous la responsabilité du praticien référent.
            </div>
          )}

          {request.consent.basis === 'none' && (
            <div className="mt-2 rounded border border-danger-200 bg-danger-50 p-2 text-danger-800">
              <span className="font-semibold">Violation des règles de gouvernance :</span> Aucune preuve de consentement n'est attachée à cette demande. Conformément à la charte fédérée, les flux inter-hospitaliers sans consentement explicite du patient sont formellement prohibés.
            </div>
          )}
        </div>

        {/* Décision d'arbitrage */}
        {decision ? (
          <div
            className={`rounded-xl border p-4 text-xs ${decision.outcome === 'approved'
              ? 'border-success-200 bg-success-50 text-success-800'
              : 'border-danger-200 bg-danger-50 text-danger-800'
              }`}
          >
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold flex items-center gap-2">
                <span>Décision de Gouvernance : {decision.outcome === 'approved' ? 'Autorisée' : 'Refusée'}</span>
                {decision.simulated && <DemoBadge>Simulée — non persistée</DemoBadge>}
              </div>
              <div className="text-[11px] opacity-75">
                Instruction par {governanceService.getPersonName(decision.decidedById)} le {new Date(decision.decidedAt).toLocaleDateString('fr-TN')}
              </div>
            </div>

            <p className="mt-2 text-xs font-medium">« {decision.rationale} »</p>

            {decision.conditions.length > 0 && (
              <div className="mt-2.5">
                <span className="font-semibold">Conditions d'exécution imposées :</span>
                <ul className="mt-1 list-disc pl-4 space-y-0.5">
                  {decision.conditions.map((condition, i) => (
                    <li key={i}>{condition}</li>
                  ))}
                </ul>
              </div>
            )}

            {proof && (
              <div className="mt-3 flex items-center justify-between border-t border-success-200/60 pt-2 font-mono text-[11px]">
                <span className="text-slate-600">Preuve cryptographique ancrée :</span>
                <span className="truncate max-w-xs">{proof.hash}</span>
              </div>
            )}
          </div>
        ) : reviewForm ? (
          reviewForm
        ) : (
          <Alert tone="warning" title="Instruction d'Arbitrage en Attente">
            Cette demande est en attente d'arbitrage par l'Autorité d'Éthique & Gouvernance. Aucun flux de données ne peut être activé entre les nœuds tant que l'autorisation n'a pas été formellement signée.
          </Alert>
        )}
      </section>
    </Card>
  )
}
