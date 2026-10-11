import { useEffect, useRef, useState } from 'react'
import {
  DEMO_MANAGER_ID,
  DEMO_ORGANIZATION_ID,
  loadOnboardingSnapshot,
  type DemoScenario,
} from './services/onboardingService'
import type { OnboardingSnapshot } from './types/onboarding'

export type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; snapshot: OnboardingSnapshot }

/**
 * Loads the MOCKED onboarding snapshot for a demo scenario and keeps local edits
 * in memory. Failure scenarios fail the first matching submission once per page load.
 */
export function useOnboardingSnapshot(scenario: DemoScenario) {
  const [load, setLoad] = useState<LoadState>({ kind: 'loading' })
  // Incremented by "Réessayer" to reload the snapshot.
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario })
      .then((snapshot) => !cancelled && setLoad({ kind: 'ready', snapshot }))
      .catch(
        (error: unknown) =>
          !cancelled &&
          setLoad({ kind: 'error', message: error instanceof Error ? error.message : String(error) }),
      )
    return () => {
      cancelled = true
    }
  }, [scenario, attempt])

  const retry = () => {
    setLoad({ kind: 'loading' })
    setAttempt((n) => n + 1)
  }

  const usedFailures = useRef(new Set<DemoScenario>())
  const failureOnce = (failure: DemoScenario) => () => {
    if (scenario !== failure || usedFailures.current.has(failure)) return false
    usedFailures.current.add(failure)
    return true
  }

  const update = (snapshot: OnboardingSnapshot) => setLoad({ kind: 'ready', snapshot })

  return { load, retry, update, failureOnce }
}
