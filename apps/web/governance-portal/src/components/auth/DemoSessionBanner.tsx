import { Badge } from '@hackcure/design-system'
import { authService, type DemoSession } from '../../services/authService'

interface DemoSessionBannerProps {
  session: DemoSession | null
  onOpenAuthModal: () => void
}

export function DemoSessionBanner({ session, onOpenAuthModal }: DemoSessionBannerProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-200 bg-amber-50/90 px-4 py-2 text-xs text-amber-900">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="warning">HC-210 D1</Badge>
        <span className="font-semibold">Session Démo :</span>
        {session ? (
          <>
            <span className="font-medium text-slate-800">{session.identity.displayName}</span>
            <span className="text-slate-500">({session.identity.role})</span>
            <span className="text-slate-400">•</span>
            <span className="text-slate-500">{session.identity.organizationName}</span>
            <span className="text-slate-400">•</span>
            <span className="font-mono text-[11px] text-slate-500">{session.sessionId}</span>
            {session.status === 'expired' && <Badge tone="danger">Expirée (401)</Badge>}
          </>
        ) : (
          <span className="text-rose-700 font-medium">Non authentifié (401)</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onOpenAuthModal}
          className="rounded-md bg-white px-2.5 py-1 font-medium text-slate-700 shadow-xs ring-1 ring-slate-200 hover:bg-slate-50"
        >
          Changer d'identité démo
        </button>
        {session && (
          <button
            type="button"
            onClick={() => authService.logout()}
            className="rounded-md bg-white px-2.5 py-1 font-medium text-rose-700 shadow-xs ring-1 ring-rose-200 hover:bg-rose-50"
          >
            Déconnexion
          </button>
        )}
      </div>
    </div>
  )
}
