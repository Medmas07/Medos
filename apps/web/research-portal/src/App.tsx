import { useEffect, useState } from 'react'
import {
  AppShell,
  Badge,
  Button,
  DemoBanner,
  ErrorState,
  LoadingState,
  SideNav,
  type SideNavItem,
  type SideNavSection,
} from '@hackcure/design-system'
import { pageStatusDisplay } from './presentation'
import {
  DEMO_RESEARCHER_ID,
  loadResearchSnapshot,
  PAGE_DEFINITIONS,
  scenarioFromSearch,
  type PageSection,
} from './services/researchService'
import type { PageId, ResearchSnapshot } from './types/research'
import { DashboardView } from './views/DashboardView'
import { HomeView } from './views/HomeView'
import { PagePlaceholderView } from './views/PagePlaceholderView'

type ViewId = 'home' | PageId

const VIEW_IDS: readonly string[] = ['home', ...PAGE_DEFINITIONS.map((d) => d.id)]

const SECTION_TITLES: Record<PageSection, string> = {
  projects: 'Projets et demandes',
  compute: 'Compute-to-Data',
  sciagents: 'Assistance scientifique',
}

function viewFromHash(): ViewId {
  const hash = window.location.hash.replace('#', '')
  return VIEW_IDS.includes(hash) ? (hash as ViewId) : 'home'
}

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; snapshot: ResearchSnapshot }

export default function App() {
  const [currentView, setCurrentView] = useState<ViewId>(viewFromHash)
  const [load, setLoad] = useState<LoadState>({ kind: 'loading' })
  // Incremented by "Réessayer" to reload the snapshot.
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const handleHashChange = () => setCurrentView(viewFromHash())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  useEffect(() => {
    let cancelled = false
    loadResearchSnapshot(DEMO_RESEARCHER_ID, { scenario: scenarioFromSearch(window.location.search) })
      .then((snapshot) => !cancelled && setLoad({ kind: 'ready', snapshot }))
      .catch(
        (error: unknown) =>
          !cancelled &&
          setLoad({ kind: 'error', message: error instanceof Error ? error.message : String(error) }),
      )
    return () => {
      cancelled = true
    }
  }, [attempt])

  const retry = () => {
    setLoad({ kind: 'loading' })
    setAttempt((n) => n + 1)
  }

  const navigateTo = (view: ViewId) => {
    setCurrentView(view)
    window.location.assign(`#${view}`)
  }

  const snapshot = load.kind === 'ready' ? load.snapshot : null

  const navItem = (view: ViewId, label: string, badge?: SideNavItem['badge']): SideNavItem => ({
    label,
    href: `#${view}`,
    current: currentView === view,
    badge,
    onClick: (e) => {
      e.preventDefault()
      navigateTo(view)
    },
  })

  const pageItems = (section: PageSection): SideNavItem[] =>
    PAGE_DEFINITIONS.filter((d) => d.section === section).map((def) => {
      const page = snapshot?.pages.find((p) => p.id === def.id)
      const badge =
        page?.status === 'locked' ? (
          <Badge tone={pageStatusDisplay.locked.tone}>{pageStatusDisplay.locked.label}</Badge>
        ) : undefined
      return navItem(def.id, def.label, badge)
    })

  const navigationSections: SideNavSection[] = [
    { items: [navItem('home', 'Accueil')] },
    ...(Object.keys(SECTION_TITLES) as PageSection[]).map((section) => ({
      title: SECTION_TITLES[section],
      items: pageItems(section),
    })),
  ]

  const renderContent = () => {
    if (load.kind === 'loading') return <LoadingState label="Chargement des projets de recherche…" />
    if (load.kind === 'error') {
      return (
        <ErrorState
          title="Projets de recherche indisponibles"
          description={load.message}
          action={<Button variant="secondary" onClick={retry}>Réessayer</Button>}
        />
      )
    }
    if (currentView === 'home') {
      return <HomeView snapshot={load.snapshot} onNavigate={navigateTo} />
    }
    if (currentView === 'dashboard') {
      return <DashboardView snapshot={load.snapshot} onNavigate={navigateTo} />
    }
    const page = load.snapshot.pages.find((p) => p.id === currentView)!
    const section = PAGE_DEFINITIONS.find((d) => d.id === currentView)!.section
    return <PagePlaceholderView page={page} section={SECTION_TITLES[section]} />
  }

  return (
    <AppShell
      productName="Portail de Recherche"
      productContext={snapshot?.organization.name ?? 'Recherche gouvernée'}
      banner={
        <DemoBanner>
          Démonstration D1 : données fictives (HC-005), service de recherche et identité simulés. Aucune
          exécution réelle, aucun accès aux Hospital Nodes, aucune connexion à SciAgents.
        </DemoBanner>
      }
      navigation={<SideNav label="Navigation principale" sections={navigationSections} />}
      sidebarFooter={
        snapshot && (
          <div className="space-y-1">
            <div className="font-semibold text-slate-800">
              {snapshot.researcher.title} {snapshot.researcher.firstName} {snapshot.researcher.lastName}
            </div>
            <div className="text-slate-500">Chercheur principal (identité simulée)</div>
          </div>
        )
      }
    >
      {renderContent()}
    </AppShell>
  )
}
