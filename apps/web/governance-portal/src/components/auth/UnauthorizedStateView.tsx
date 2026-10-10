import { Button, Card, DemoBanner } from '@hackcure/design-system'
import { authService, type DemoSession } from '../../services/authService'

interface UnauthorizedStateViewProps {
  session: DemoSession | null
  onOpenAuthModal: () => void
}

export function UnauthorizedStateView({ session, onOpenAuthModal }: UnauthorizedStateViewProps) {
  const isExpired = session?.status === 'expired'
  const isUnauthorizedRole = session && session.status === 'active' && session.identity.role !== 'governance_reviewer'

  const handleSwitchToReviewer = () => {
    authService.login('usr-olfa', { scenario: 'nominal' })
  }

  return (
    <div className="mx-auto max-w-2xl py-12">
      <Card>
        <div className="space-y-6 p-6">
          <DemoBanner>
            Démonstration D1 : contrôle d'accès déterministe (HC-210). Les états 401 et 403 sont simulés explicitement
            pour la validation de la sécurité.
          </DemoBanner>

          <div className="text-center">
            <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-full bg-rose-100 text-2xl text-rose-600">
              {isExpired ? '⏳' : '🔒'}
            </div>

            <h2 className="text-2xl font-bold text-slate-900">
              {isExpired
                ? 'Session démo expirée (401)'
                : isUnauthorizedRole
                ? 'Accès refusé — Rôle non autorisé (403)'
                : 'Session non authentifiée (401)'}
            </h2>

            <p className="mt-2 text-sm text-slate-600">
              {isExpired ? (
                <>
                  La session démo simulée pour <strong>{session?.identity.displayName}</strong> a expiré.
                  Conformément au scénario D1, les appels d'API et l'accès au portail sont révoqués.
                </>
              ) : isUnauthorizedRole ? (
                <>
                  L'identité connectée <strong>{session.identity.displayName}</strong> dispose du rôle{' '}
                  <code className="rounded bg-slate-100 px-1 py-0.5 text-slate-800">{session.identity.role}</code> au
                  sein de <em>{session.identity.organizationName}</em>. Seul le rôle{' '}
                  <code className="rounded bg-slate-100 px-1 py-0.5 text-slate-800">governance_reviewer</code> est
                  autorisé à consulter et instruire les dossiers de gouvernance fédérée.
                </>
              ) : (
                'Aucune session active détectée. Veuillez vous connecter pour accéder au portail.'
              )}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
            <div className="font-semibold text-slate-800">État du contexte de sécurité D1 :</div>
            <ul className="mt-2 space-y-1 list-disc pl-4">
              <li>Identité courante : {session ? `${session.identity.displayName} (${session.identity.id})` : 'Aucune'}</li>
              <li>Rôle déclaré : {session?.identity.role ?? 'Aucun'}</li>
              <li>Statut de session : {session?.status ?? 'Non connecté'}</li>
              <li>Code HTTP simulé : {isExpired ? '401 Unauthorized' : isUnauthorizedRole ? '403 Forbidden' : '401 Unauthorized'}</li>
            </ul>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Button variant="secondary" onClick={onOpenAuthModal}>
              Choisir une autre identité démo
            </Button>
            {isUnauthorizedRole && (
              <Button variant="primary" onClick={handleSwitchToReviewer}>
                Se connecter en tant que Pr Olfa Hamdi (Réviseure)
              </Button>
            )}
            {isExpired && (
              <Button variant="primary" onClick={() => authService.login(session.identity.id, { scenario: 'nominal' })}>
                Renouveler la session (200 OK)
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
