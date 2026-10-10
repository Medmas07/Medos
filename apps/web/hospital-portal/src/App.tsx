import { useEffect, useRef, useState } from 'react'
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
import { stepStatusDisplay } from './presentation'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  loadOnboardingSnapshot,
  scenarioFromSearch,
  STEP_DEFINITIONS,
  type DemoScenario,
  type StepSection,
} from './services/onboardingService'
import type { OnboardingSnapshot, StepId } from './types/onboarding'
import { AgreementsView } from './views/AgreementsView'
import { AutomatedReviewView } from './views/AutomatedReviewView'
import { DmiView } from './views/DmiView'
import { DocumentsView } from './views/DocumentsView'
import { HumanReviewView } from './views/HumanReviewView'
import { OverviewView } from './views/OverviewView'
import { ProfileView } from './views/ProfileView'
import { RegistrationView } from './views/RegistrationView'
import { TechnicalView } from './views/TechnicalView'
import { StepPlaceholderView } from './views/StepPlaceholderView'

type ViewId = 'overview' | StepId

const VIEW_IDS: readonly string[] = ['overview', ...STEP_DEFINITIONS.map((d) => d.id)]

function viewFromHash(): ViewId {
  const hash = window.location.hash.replace('#', '')
  return VIEW_IDS.includes(hash) ? (hash as ViewId) : 'overview'
}

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; snapshot: OnboardingSnapshot }

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
    loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, {
      scenario: scenarioFromSearch(window.location.search),
    })
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

  // Failure scenarios fail the first matching submission once per page load.
  const usedFailures = useRef(new Set<DemoScenario>())
  const failureOnce = (scenario: DemoScenario) => () => {
    if (scenarioFromSearch(window.location.search) !== scenario || usedFailures.current.has(scenario)) return false
    usedFailures.current.add(scenario)
    return true
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

  const stepItems = (section: StepSection): SideNavItem[] =>
    STEP_DEFINITIONS.filter((d) => d.section === section).map((def) => {
      const step = snapshot?.steps.find((s) => s.id === def.id)
      const badge =
        step && (step.status === 'attention' || step.status === 'in_progress') ? (
          <Badge tone={stepStatusDisplay[step.status].tone} dot>
            {stepStatusDisplay[step.status].label}
          </Badge>
        ) : undefined
      return navItem(def.id, def.navLabel, badge)
    })

  const navigationSections: SideNavSection[] = [
    { items: [navItem('overview', 'Tableau de bord')] },
    { title: "Parcours d'adhésion", items: stepItems('onboarding') },
    { title: 'Hospital Node', items: stepItems('node') },
  ]

  const renderContent = () => {
    if (load.kind === 'loading') return <LoadingState label="Chargement du dossier d'adhésion…" />
    if (load.kind === 'error') {
      return (
        <ErrorState
          title="Dossier d'adhésion indisponible"
          description={load.message}
          action={<Button variant="secondary" onClick={retry}>Réessayer</Button>}
        />
      )
    }
    if (currentView === 'overview') {
      return <OverviewView snapshot={load.snapshot} onNavigate={navigateTo} />
    }
    if (currentView === 'registration') {
      return (
        <RegistrationView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('registration-failure')}
          // Local state only: a reload returns to the fixture snapshot.
          onRegistered={(snapshot) => setLoad({ kind: 'ready', snapshot })}
          onNavigate={navigateTo}
        />
      )
    }
    if (currentView === 'profile') {
      return (
        <ProfileView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('profile-failure')}
          onUpdated={(snapshot) => setLoad({ kind: 'ready', snapshot })}
          onNavigate={navigateTo}
        />
      )
    }
    if (currentView === 'documents') {
      return (
        <DocumentsView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('document-failure')}
          onUpdated={(snapshot) => setLoad({ kind: 'ready', snapshot })}
          onNavigate={navigateTo}
        />
      )
    }
    if (currentView === 'agreements') {
      return (
        <AgreementsView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('agreement-failure')}
          onUpdated={(snapshot) => setLoad({ kind: 'ready', snapshot })}
          onNavigate={navigateTo}
        />
      )
    }
    if (currentView === 'technical') {
      return (
        <TechnicalView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('technical-failure')}
          onUpdated={(snapshot) => setLoad({ kind: 'ready', snapshot })}
          onNavigate={navigateTo}
        />
      )
    }
    if (currentView === 'dmi') {
      return (
        <DmiView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('dmi-failure')}
          onUpdated={(snapshot) => setLoad({ kind: 'ready', snapshot })}
          onNavigate={navigateTo}
        />
      )
    }
    if (currentView === 'automated-review') {
      return (
        <AutomatedReviewView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('submission-failure')}
          onUpdated={(snapshot) => setLoad({ kind: 'ready', snapshot })}
          onNavigate={navigateTo}
        />
      )
    }
    if (currentView === 'human-review') {
      return (
        <HumanReviewView
          snapshot={load.snapshot}
          consumeSimulatedFailure={failureOnce('refresh-failure')}
          onNavigate={navigateTo}
        />
      )
    }
    const index = load.snapshot.steps.findIndex((s) => s.id === currentView)
    return <StepPlaceholderView step={load.snapshot.steps[index]} position={index + 1} />
  }

  return (
    <AppShell
      productName="Portail Hospitalier"
      productContext={snapshot?.organization.name ?? 'Adhésion des établissements'}
      banner={
        <DemoBanner>
          Démonstration D1 : données fictives (HC-005), service d'adhésion et identité simulés. Aucune
          connexion à un DMI ni à une base hospitalière.
        </DemoBanner>
      }
      navigation={<SideNav label="Navigation principale" sections={navigationSections} />}
      sidebarFooter={
        snapshot && (
          <div className="space-y-1">
            <div className="font-semibold text-slate-800">
              {snapshot.manager.firstName} {snapshot.manager.lastName}
            </div>
            <div className="text-slate-500">Responsable d'établissement (identité simulée)</div>
          </div>
        )
      }
    >
      {renderContent()}
    </AppShell>
  )
}
