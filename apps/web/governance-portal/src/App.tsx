import { useEffect, useState, useSyncExternalStore } from 'react'
import {
  AppShell,
  Badge,
  SideNav,
  ThemeToggle,
  type SideNavSection,
} from '@hackcure/design-system'
import { OverviewView } from './components/views/OverviewView'
import { HospitalOnboardingView } from './components/views/HospitalOnboardingView'
import { DataSyncView } from './components/views/DataSyncView'
import { ResearchRequestsView } from './components/views/ResearchRequestsView'
import { AuditExplorerView } from './components/views/AuditExplorerView'
import { VerifierView } from './components/views/VerifierView'
import { StateShowcaseView } from './components/views/StateShowcaseView'
import { NotificationsView } from './components/views/NotificationsView'
import { governanceService } from './services/governanceService'
import { notificationStore, applyReadOverrides, countNotifications, notificationRows } from './services/notificationService'
import { reviewStore } from './services/reviewStore'
import { authService } from './services/authService'
import { DemoAuthModal } from './components/auth/DemoAuthModal'
import { UnauthorizedStateView } from './components/auth/UnauthorizedStateView'

type ViewId =
  | 'overview'
  | 'onboarding'
  | 'synchronizations'
  | 'research'
  | 'audit'
  | 'notifications'
  | 'verifier'
  | 'states'

export default function App() {
  const [currentView, setCurrentView] = useState<ViewId>('overview')
  const [inspectedProofId, setInspectedProofId] = useState<string>('proof-003')
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)

  // Simulated decisions (HC-073) change the counts below; re-render when they do.
  useSyncExternalStore(reviewStore.subscribe, reviewStore.getSnapshot)
  // Re-render when notification read state changes (HC-200).
  useSyncExternalStore(notificationStore.subscribe, () => notificationStore.getSnapshot())
  // HC-210: Reactive demo authentication session.
  const session = useSyncExternalStore(authService.subscribe, authService.getSnapshot)

  // Sync with URL hash if present
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as ViewId
      if (
        [
          'overview',
          'onboarding',
          'synchronizations',
          'research',
          'audit',
          'notifications',
          'verifier',
          'states',
        ].includes(hash)
      ) {
        setCurrentView(hash)
      }
    }

    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const navigateTo = (view: ViewId) => {
    setCurrentView(view)
    window.location.hash = view
  }

  const handleInspectProof = (proofId: string) => {
    setInspectedProofId(proofId)
    navigateTo('verifier')
  }

  const applications = governanceService.getHospitalApplications()
  const syncs = governanceService.getSynchronizationRequests()
  const research = governanceService.getResearchAccessRequests()
  const proofs = governanceService.getLedgerProofs()

  const pendingAppsCount = applications.filter((a) => a.status === 'human_review' || a.status === 'pending').length
  const pendingSyncsCount = syncs.filter((s) => s.status === 'pending').length
  const underReviewResearchCount = research.filter((r) => r.status === 'under_review').length

  // HC-200: Notification unread count with session overrides.
  const rawNotifs = applyReadOverrides(governanceService.getReviewerNotifications('usr-olfa'))
  const unreadNotifCount = countNotifications(notificationRows(rawNotifs)).unread

  const navigationSections: SideNavSection[] = [
    {
      title: 'Gouvernance Fédérée',
      items: [
        {
          label: "Vue d'ensemble",
          href: '#overview',
          current: currentView === 'overview',
          onClick: (e) => {
            e.preventDefault()
            navigateTo('overview')
          },
        },
        {
          label: 'Adhésions Hospitalières',
          href: '#onboarding',
          current: currentView === 'onboarding',
          badge: pendingAppsCount > 0 ? <Badge tone="warning" dot>{pendingAppsCount}</Badge> : undefined,
          onClick: (e) => {
            e.preventDefault()
            navigateTo('onboarding')
          },
        },
        {
          label: 'Synchronisations Soins',
          href: '#synchronizations',
          current: currentView === 'synchronizations',
          badge: pendingSyncsCount > 0 ? <Badge tone="warning" dot>{pendingSyncsCount}</Badge> : undefined,
          onClick: (e) => {
            e.preventDefault()
            navigateTo('synchronizations')
          },
        },
        {
          label: 'Accès Recherche',
          href: '#research',
          current: currentView === 'research',
          badge: underReviewResearchCount > 0 ? <Badge tone="info" dot>{underReviewResearchCount}</Badge> : undefined,
          onClick: (e) => {
            e.preventDefault()
            navigateTo('research')
          },
        },
        {
          label: 'Piste d’Audit & Registre',
          href: '#audit',
          current: currentView === 'audit',
          badge: <Badge tone="neutral">{proofs.length}</Badge>,
          onClick: (e) => {
            e.preventDefault()
            navigateTo('audit')
          },
        },
        {
          label: 'Notifications',
          href: '#notifications',
          current: currentView === 'notifications',
          badge: unreadNotifCount > 0 ? <Badge tone="danger" dot>{unreadNotifCount}</Badge> : undefined,
          onClick: (e) => {
            e.preventDefault()
            navigateTo('notifications')
          },
        },
      ],
    },
    {
      title: 'Outils & Démonstration',
      items: [
        {
          label: 'Vérificateur de Preuves',
          href: '#verifier',
          current: currentView === 'verifier',
          onClick: (e) => {
            e.preventDefault()
            navigateTo('verifier')
          },
        },
        {
          label: 'États Résilients D1',
          href: '#states',
          current: currentView === 'states',
          onClick: (e) => {
            e.preventDefault()
            navigateTo('states')
          },
        },
      ],
    },
  ]

  const isAuthorized = authService.isAuthorizedForGovernance(session)

  return (
    <>
      <AppShell
        productName="Portail de Gouvernance"
        productContext="Autorité de Gouvernance et d'Éthique Fédérée"
        toolbar={<ThemeToggle />}
        pageKey={currentView}
        navigation={<SideNav label="Navigation principale" sections={navigationSections} />}
        sidebarFooter={
          session ? (
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-ink">{session.identity.displayName}</span>
                {session.status === 'expired' && <Badge tone="danger">Expirée</Badge>}
              </div>
              <div className="text-ink-muted">
                {session.identity.role === 'governance_reviewer' ? 'Réviseure de gouvernance' : session.identity.role} (
                {session.identity.id})
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-ink-soft">
                <span className="size-2 rounded-full bg-success-600" />
                <span>Nœud de Gouvernance en ligne</span>
              </div>
              <div className="flex items-center gap-3 pt-1 text-[11px]">
                <button
                  type="button"
                  onClick={() => setIsAuthModalOpen(true)}
                  className="font-medium text-brand-700 hover:underline"
                >
                  Changer d'identité
                </button>
                <button type="button" onClick={() => authService.logout()} className="font-medium text-ink-soft hover:text-ink">
                  Déconnexion
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="font-semibold text-ink">Non authentifié</div>
              <button
                type="button"
                onClick={() => setIsAuthModalOpen(true)}
                className="text-[11px] font-medium text-brand-700 hover:underline"
              >
                Se connecter (démo)
              </button>
            </div>
          )
        }
      >
        {!isAuthorized ? (
          <UnauthorizedStateView session={session} onOpenAuthModal={() => setIsAuthModalOpen(true)} />
        ) : (
          <>
            {currentView === 'overview' && <OverviewView onNavigate={(v) => navigateTo(v as ViewId)} />}
            {currentView === 'onboarding' && <HospitalOnboardingView />}
            {currentView === 'synchronizations' && <DataSyncView />}
            {currentView === 'research' && <ResearchRequestsView />}
            {currentView === 'audit' && <AuditExplorerView onInspectProof={handleInspectProof} />}
            {currentView === 'notifications' && <NotificationsView />}
            {currentView === 'verifier' && <VerifierView initialProofId={inspectedProofId} />}
            {currentView === 'states' && <StateShowcaseView />}
          </>
        )}
      </AppShell>

      <DemoAuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />
    </>
  )
}
