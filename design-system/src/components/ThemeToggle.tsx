import type { ReactNode } from 'react'
import { cx } from '../cx'
import { useTheme, type ThemePreference } from '../theme'
import { MonitorIcon, MoonIcon, SunIcon } from './icons'

export interface ThemeToggleProps {
  /** Accessible group name. */
  label?: string
  /** Button labels, shown as tooltips and to assistive technology. */
  labels?: Record<ThemePreference, string>
  className?: string
}

const icons: Record<ThemePreference, (className: string) => ReactNode> = {
  system: (className) => <MonitorIcon className={className} />,
  light: (className) => <SunIcon className={className} />,
  dark: (className) => <MoonIcon className={className} />,
}

const order: readonly ThemePreference[] = ['system', 'light', 'dark']

/** Segmented control for the light / dark / system theme choice. */
export function ThemeToggle({
  label = 'Thème',
  labels = { system: 'Thème du système', light: 'Thème clair', dark: 'Thème sombre' },
  className,
}: ThemeToggleProps) {
  const { preference, setPreference } = useTheme()
  return (
    <div
      role="group"
      aria-label={label}
      className={cx(
        'inline-flex shrink-0 items-center gap-0.5 rounded-full bg-surface-muted p-[3px]',
        className,
      )}
    >
      {order.map((choice) => {
        const active = preference === choice
        return (
          <button
            key={choice}
            type="button"
            aria-pressed={active}
            aria-label={labels[choice]}
            title={labels[choice]}
            onClick={() => setPreference(choice)}
            className={cx(
              'hc-press grid h-[30px] w-[34px] place-items-center rounded-full transition-colors duration-200',
              active
                ? 'bg-surface-raised text-ink shadow-card'
                : 'text-ink-muted hover:text-ink',
            )}
          >
            {icons[choice]('size-4')}
          </button>
        )
      })}
    </div>
  )
}
