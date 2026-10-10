import { useEffect, useState } from 'react'
import {
  AppShell,
  Badge,
  DemoBanner,
  SideNav,
  type SideNavSection,
} from '@hackcure/design-system'
import { OverviewView } from './components/views/OverviewView'
import { HospitalOnboardingView } from './components/views/HospitalOnboardingView'
import { DataSyncView } from './components/views/DataSyncView'
import { ResearchRequestsView } from './components/views/ResearchRequestsView'
import { AuditExplorerView } from './components/views/AuditExplorerView'
import { VerifierView } from './components/views/VerifierView'
import { StateShowcaseView } from './components/views/StateShowcaseView'
import { governanceService } from './services/governanceService'

type ViewId =
  | 'overview'
  | 'onboarding'
  | 'synchronizations'
  | 'research'
  | 'audit'
  | 'verifier'
  | 'states'

export default function App() {
  const [currentView, setCurrentView] = useState<ViewId>('overview')
  const [inspectedProofId, setInspectedProofId] = useState<string>('proof-003')

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

  return (
    <AppShell
      productName="Portail de Gouvernance"
      productContext="Autorité de Gouvernance et d'Éthique Fédérée"
      banner={
        <DemoBanner>
          Démonstration D1. Données fictives (HC-005) & preuves de registre simulées. Aucun accès direct aux bases hospitalières.
        </DemoBanner>
      }
      navigation={<SideNav label="Navigation principale" sections={navigationSections} />}
      sidebarFooter={
        <div className="space-y-1">
          <div className="font-semibold text-slate-800">Pr Olfa Hamdi</div>
          <div className="text-slate-500">Réviseure de gouvernance (usr-olfa)</div>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-slate-600">
            <span className="size-2 rounded-full bg-emerald-500" />
            <span>Nœud de Gouvernance en ligne</span>
          </div>
        </div>
      }
    >
      {currentView === 'overview' && <OverviewView onNavigate={(v) => navigateTo(v as ViewId)} />}
      {currentView === 'onboarding' && <HospitalOnboardingView />}
      {currentView === 'synchronizations' && <DataSyncView />}
      {currentView === 'research' && <ResearchRequestsView />}
      {currentView === 'audit' && <AuditExplorerView onInspectProof={handleInspectProof} />}
      {currentView === 'verifier' && <VerifierView initialProofId={inspectedProofId} />}
      {currentView === 'states' && <StateShowcaseView />}
    </AppShell>
  )
}
