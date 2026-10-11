import type { DemoScenario } from '../services/onboardingService'
import type { OnboardingSnapshot, StepId } from '../types/onboarding'
import { AgreementsView } from './AgreementsView'
import { AutomatedReviewView } from './AutomatedReviewView'
import { DecisionView } from './DecisionView'
import { DmiView } from './DmiView'
import { DocumentsView } from './DocumentsView'
import { HumanReviewView } from './HumanReviewView'
import { InstallationView } from './InstallationView'
import { NodeConfigurationView } from './NodeConfigurationView'
import { NodeDownloadView } from './NodeDownloadView'
import { NodeStatusView } from './NodeStatusView'
import { ProfileView } from './ProfileView'
import { RegistrationView } from './RegistrationView'
import { TechnicalView } from './TechnicalView'

interface StepViewProps {
  step: StepId
  snapshot: OnboardingSnapshot
  /** Local state only: a reload returns to the fixture snapshot. */
  onUpdated: (snapshot: OnboardingSnapshot) => void
  /** Returns a callback that is true once when the demo scenario should fail that request. */
  failureOnce: (scenario: DemoScenario) => () => boolean
  onNavigate: (step: StepId) => void
}

/** One onboarding or Hospital Node page, shared by the portal shell and the guided journey. */
export function StepView({ step, snapshot, onUpdated, failureOnce, onNavigate }: StepViewProps) {
  switch (step) {
    case 'registration':
      return (
        <RegistrationView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('registration-failure')}
          onRegistered={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'profile':
      return (
        <ProfileView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('profile-failure')}
          onUpdated={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'documents':
      return (
        <DocumentsView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('document-failure')}
          onUpdated={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'agreements':
      return (
        <AgreementsView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('agreement-failure')}
          onUpdated={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'technical':
      return (
        <TechnicalView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('technical-failure')}
          onUpdated={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'dmi':
      return (
        <DmiView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('dmi-failure')}
          onUpdated={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'automated-review':
      return (
        <AutomatedReviewView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('submission-failure')}
          onUpdated={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'human-review':
      return (
        <HumanReviewView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('refresh-failure')}
          onNavigate={onNavigate}
        />
      )
    case 'decision':
      return <DecisionView snapshot={snapshot} onNavigate={onNavigate} />
    case 'node-configuration':
      return <NodeConfigurationView snapshot={snapshot} onNavigate={onNavigate} />
    case 'node-download':
      return (
        <NodeDownloadView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('download-failure')}
          onUpdated={onUpdated}
          onNavigate={onNavigate}
        />
      )
    case 'node-installation':
      return <InstallationView snapshot={snapshot} onUpdated={onUpdated} onNavigate={onNavigate} />
    case 'node-status':
      return (
        <NodeStatusView
          snapshot={snapshot}
          consumeSimulatedFailure={failureOnce('node-status-failure')}
          onNavigate={onNavigate}
        />
      )
  }
}
