import { useEffect } from 'react'
import { Lock } from 'lucide-react'
import { Alert, Button, ErrorState, LoadingState, ThemeToggle } from '@hackcure/design-system'
import { SIGN_IN_HREF } from './landing/links'
import { Logo } from './landing/Logo'
import { stepStatusDisplay } from './presentation'
import { journeyHref } from './route'
import { nodeConfiguration } from './services/nodeConfigService'
import { scenarioFromSearch } from './services/onboardingService'
import type { OnboardingSnapshot, StepId, StepStatus } from './types/onboarding'
import { useOnboardingSnapshot } from './useOnboardingSnapshot'
import { StepView } from './views/StepView'

interface JourneyPhase {
  title: string
  steps: { id: StepId; label: string }[]
}

/**
 * The guided path from the landing page's "Télécharger l'instance" button: the
 * onboarding forms one after the other, the Governance review, then the Node
 * configuration guide before the download button. Approval stays with the
 * Governance / Ethics Authority; this journey only displays it.
 */
const JOURNEY: readonly JourneyPhase[] = [
  {
    title: "Formulaires d'adhésion",
    steps: [
      { id: 'registration', label: 'Inscription' },
      { id: 'profile', label: "Profil de l'établissement" },
      { id: 'documents', label: 'Documents administratifs' },
      { id: 'agreements', label: 'Accords' },
      { id: 'technical', label: 'Questionnaire technique' },
      { id: 'dmi', label: 'Questionnaire DMI / SIH' },
    ],
  },
  {
    title: 'Soumission et validation',
    steps: [
      { id: 'automated-review', label: 'Contrôles et soumission' },
      { id: 'human-review', label: 'Revue humaine' },
      { id: 'decision', label: 'Décision de gouvernance' },
    ],
  },
  {
    title: 'Instance hospitalière',
    steps: [
      { id: 'node-configuration', label: 'Guide de configuration' },
      { id: 'node-download', label: "Télécharger l'instance" },
      { id: 'node-installation', label: "Guide d'installation" },
      { id: 'node-status', label: 'État du nœud' },
    ],
  },
]

const ORDER: readonly StepId[] = JOURNEY.flatMap((phase) => phase.steps.map((s) => s.id))
const LABELS = new Map(JOURNEY.flatMap((phase) => phase.steps.map((s) => [s.id, s.label] as const)))
const NODE_STEPS: readonly StepId[] = ['node-configuration', 'node-download', 'node-installation', 'node-status']

/** The journey starts from an empty dossier unless a `?demo=` scenario is given. */
function journeyScenario() {
  const search = window.location.search
  return new URLSearchParams(search).has('demo') ? scenarioFromSearch(search) : 'empty'
}

/** Reloads the journey on the labelled demo scenario that simulates a received approval. */
const APPROVED_DEMO_HREF = `${import.meta.env.BASE_URL}?demo=decision-approuvee${journeyHref('node-configuration')}`

export function JourneyApp({ step }: { step: StepId }) {
  const { load, retry, update, failureOnce } = useOnboardingSnapshot(journeyScenario())
  const navigateTo = (next: StepId) => window.location.assign(journeyHref(next))

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [step])

  const snapshot = load.kind === 'ready' ? load.snapshot : null
  const index = ORDER.indexOf(step)
  const current = index === -1 ? 0 : index
  const previous = ORDER[current - 1]
  const next = ORDER[current + 1]

  return (
    <div className="min-h-dvh bg-paper">
      <header className="sticky top-0 z-30 border-b border-line bg-paper/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1320px] items-center justify-between gap-4 px-4 sm:px-8">
          <a href={import.meta.env.BASE_URL} aria-label="Accueil MedOS" className="rounded-lg">
            <Logo />
          </a>
          <div className="flex items-center gap-2">
            <a
              href={SIGN_IN_HREF}
              className="rounded-full px-3 py-1.5 text-[13px] font-medium text-ink-soft transition-colors hover:text-ink"
            >
              Se connecter
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1320px] gap-8 px-4 py-8 sm:px-8 lg:grid-cols-[17rem_1fr] lg:py-10">
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <JourneyProgress current={step} snapshot={snapshot} onNavigate={navigateTo} />
        </aside>

        <main className="min-w-0 space-y-6">
          {load.kind === 'loading' && <LoadingState variant="skeleton" label="Chargement du dossier d'adhésion…" />}
          {load.kind === 'error' && (
            <ErrorState
              title="Dossier d'adhésion indisponible"
              description={load.message}
              action={<Button variant="secondary" onClick={retry}>Réessayer</Button>}
            />
          )}
          {load.kind === 'ready' && (
            <>
              {(step === 'decision' || step === 'human-review' || NODE_STEPS.includes(step)) &&
                nodeConfiguration(load.snapshot).kind === 'awaiting_decision' && <AwaitingApproval />}
              <div key={step} className="animate-page">
                <StepView
                  step={step}
                  snapshot={load.snapshot}
                  onUpdated={update}
                  failureOnce={failureOnce}
                  onNavigate={navigateTo}
                />
              </div>
            </>
          )}

          <nav aria-label="Étapes du parcours" className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-6">
            {previous ? (
              <Button variant="ghost" onClick={() => navigateTo(previous)}>
                ← {LABELS.get(previous)}
              </Button>
            ) : (
              <a href={import.meta.env.BASE_URL} className="text-sm font-medium text-ink-soft hover:text-ink">
                ← Retour à l'accueil
              </a>
            )}
            {next && (
              <Button variant={step === 'node-configuration' ? 'primary' : 'secondary'} onClick={() => navigateTo(next)}>
                {step === 'node-configuration' ? "Télécharger l'instance →" : `${LABELS.get(next)} →`}
              </Button>
            )}
          </nav>
        </main>
      </div>
    </div>
  )
}

function JourneyProgress({
  current,
  snapshot,
  onNavigate,
}: {
  current: StepId
  snapshot: OnboardingSnapshot | null
  onNavigate: (step: StepId) => void
}) {
  const position = ORDER.indexOf(current) + 1
  return (
    <nav aria-label="Progression du parcours" className="rounded-2xl border border-line bg-surface p-4 shadow-card">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[13px] font-semibold text-ink">Parcours d'adhésion</p>
        <span className="tabular text-xs text-ink-muted">
          {position} / {ORDER.length}
        </span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-muted" aria-hidden>
        <div
          className="h-full rounded-full bg-brand-500 transition-[width] duration-500 ease-(--ease-out)"
          style={{ width: `${(position / ORDER.length) * 100}%` }}
        />
      </div>
      {/* The full list is a sidebar on wide screens; phones keep only the bar and the current step. */}
      <p className="mt-3 text-sm font-medium text-ink lg:hidden">{LABELS.get(current)}</p>
      <ol className="mt-5 hidden space-y-5 lg:block">
        {JOURNEY.map((phase) => (
          <li key={phase.title}>
            <p className="text-[11px] font-semibold tracking-[0.08em] text-ink-muted uppercase">{phase.title}</p>
            <ol className="mt-2 space-y-0.5">
              {phase.steps.map((s) => {
                const state = snapshot?.steps.find((x) => x.id === s.id)
                const display = state ? stepStatusDisplay[state.status] : null
                const isCurrent = s.id === current
                return (
                  <li key={s.id}>
                    <a
                      href={journeyHref(s.id)}
                      aria-current={isCurrent ? 'step' : undefined}
                      onClick={(e) => {
                        e.preventDefault()
                        onNavigate(s.id)
                      }}
                      className={`flex items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-[13px] transition-colors ${
                        isCurrent ? 'bg-brand-100 font-semibold text-ink' : 'text-ink-soft hover:bg-surface-muted hover:text-ink'
                      }`}
                    >
                      <span className="min-w-0 truncate">{s.label}</span>
                      {display && state && state.status !== 'pending' && (
                        <StatusMark status={state.status} label={display.label} />
                      )}
                    </a>
                  </li>
                )
              })}
            </ol>
          </li>
        ))}
      </ol>
    </nav>
  )
}

const MARK_COLORS: Partial<Record<StepStatus, string>> = {
  completed: 'bg-success-600',
  attention: 'bg-warning-600',
  in_progress: 'bg-info-600',
  rejected: 'bg-danger-600',
}

/** Compact step status for the sidebar, so the step labels stay readable. */
function StatusMark({ status, label }: { status: StepStatus; label: string }) {
  if (status === 'locked') {
    return <Lock role="img" aria-label={label} className="size-3.5 shrink-0 text-ink-muted" strokeWidth={2} />
  }
  return <span role="img" aria-label={label} title={label} className={`size-2 shrink-0 rounded-full ${MARK_COLORS[status] ?? 'bg-line-strong'}`} />
}

function AwaitingApproval() {
  return (
    <Alert
      tone="info"
      title="L'approbation appartient à l'Autorité de gouvernance"
      actions={
        <a
          href={APPROVED_DEMO_HREF}
          className="inline-flex h-9 items-center rounded-full bg-primary px-4 text-[13px] font-semibold text-on-primary"
        >
          Voir la suite avec une décision simulée
        </a>
      }
    >
      MedOS ne valide pas sa propre demande : la configuration et le téléchargement de l'instance s'ouvrent après la
      décision de l'Autorité, prise dans le Governance Portal. Pour la démonstration, un scénario étiqueté charge le dossier
      fictif Cap Azur avec une approbation simulée (vos saisies locales ne sont pas conservées).
    </Alert>
  )
}
