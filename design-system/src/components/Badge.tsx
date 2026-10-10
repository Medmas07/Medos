import type { ReactNode } from 'react'
import { cx } from '../cx'
import type { Tone } from '../tone'
import { FlaskIcon } from './icons'

export interface BadgeProps {
  tone?: Tone
  /** Shows a leading status dot. */
  dot?: boolean
  children: ReactNode
  className?: string
}

const badgeTones: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  info: 'bg-info-50 text-info-700 ring-info-200',
  success: 'bg-success-50 text-success-700 ring-success-200',
  warning: 'bg-warning-50 text-warning-800 ring-warning-200',
  danger: 'bg-danger-50 text-danger-700 ring-danger-200',
  demo: 'bg-demo-50 text-demo-700 ring-demo-200',
}

const dotTones: Record<Tone, string> = {
  neutral: 'bg-slate-500',
  info: 'bg-info-600',
  success: 'bg-success-600',
  warning: 'bg-warning-600',
  danger: 'bg-danger-600',
  demo: 'bg-demo-600',
}

/**
 * Short status label. The text carries the meaning; the tone reinforces it.
 * Portals map their own domain statuses (for example "Pending review") to tones.
 */
export function Badge({ tone = 'neutral', dot = false, children, className }: BadgeProps) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset',
        badgeTones[tone],
        className,
      )}
    >
      {dot && <span aria-hidden="true" className={cx('size-1.5 rounded-full', dotTones[tone])} />}
      {children}
    </span>
  )
}

export interface DemoBadgeProps {
  children?: ReactNode
  className?: string
}

/** Marks a single value, panel, or action as MOCKED / fictional. */
export function DemoBadge({ children = 'Demo data', className }: DemoBadgeProps) {
  return (
    <Badge tone="demo" className={className}>
      <FlaskIcon className="size-3.5" />
      {children}
    </Badge>
  )
}

export interface DemoBannerProps {
  children?: ReactNode
}

/** Page-wide notice that the surface shows fictional data and simulated behaviour. */
export function DemoBanner({
  children = 'Demonstration environment. All people, organizations, and records are fictional, and integrations are simulated. Not for clinical use.',
}: DemoBannerProps) {
  return (
    <div
      role="note"
      className="flex items-center justify-center gap-2 bg-demo-700 px-4 py-1.5 text-center text-xs font-medium text-white"
    >
      <FlaskIcon className="size-4 shrink-0" />
      <span>{children}</span>
    </div>
  )
}
