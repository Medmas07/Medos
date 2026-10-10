import { useSyncExternalStore } from 'react'

/** Saved theme choice. `system` follows `prefers-color-scheme`. */
export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

/** localStorage key read by the inline script in each portal's index.html. */
export const THEME_STORAGE_KEY = 'hc-theme'

const listeners = new Set<() => void>()
let preference: ThemePreference = readPreference()

function readPreference(): ThemePreference {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY)
    return saved === 'light' || saved === 'dark' ? saved : 'system'
  } catch {
    return 'system'
  }
}

function systemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function resolve(choice: ThemePreference): ResolvedTheme {
  return choice === 'system' ? systemTheme() : choice
}

function apply(theme: ResolvedTheme) {
  document.documentElement.dataset.theme = theme
}

function notify() {
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  const onSystemChange = () => {
    if (preference === 'system') apply(systemTheme())
  }
  media.addEventListener('change', onSystemChange)
  return () => {
    listeners.delete(listener)
    media.removeEventListener('change', onSystemChange)
  }
}

/** Saves the choice and applies it, cross-fading through a View Transition when allowed. */
export function setThemePreference(choice: ThemePreference) {
  preference = choice
  try {
    if (choice === 'system') window.localStorage.removeItem(THEME_STORAGE_KEY)
    else window.localStorage.setItem(THEME_STORAGE_KEY, choice)
  } catch {
    // Storage may be unavailable (private mode); the choice then lasts for this page only.
  }
  const next = resolve(choice)
  const changes = document.documentElement.dataset.theme !== next
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (changes && !reduceMotion && 'startViewTransition' in document) {
    document.startViewTransition(() => apply(next))
  } else {
    apply(next)
  }
  notify()
}

/** Current theme choice and a setter; all callers share one store. */
export function useTheme() {
  const current = useSyncExternalStore(
    subscribe,
    () => preference,
    () => 'system' as ThemePreference,
  )
  return { preference: current, setPreference: setThemePreference }
}
