import type { MouseEventHandler, ReactNode } from 'react'
import { cx } from '../cx'
import type { Tone } from '../tone'
import { Skeleton } from './Skeleton'

export interface StatCardProps {
  /** What the number counts, for example "Pending applications". */
  label: ReactNode
  /** The figure itself; numbers render with tabular digits. */
  value: ReactNode
  /** One supporting line under the value, for example a breakdown. */
  hint?: ReactNode
  /** Optional small icon shown in a tinted tile. */
  icon?: ReactNode
  /** Tints the icon tile; `neutral` uses the brand mint. */
  tone?: Tone
  /** Rendered top right, for example a status `Badge` or `DemoBadge`. */
  badge?: ReactNode
  /** Makes the whole tile a button (for example, to open the matching page). */
  onClick?: MouseEventHandler<HTMLButtonElement>
  /** Shows a skeleton in place of the value. */
  loading?: boolean
  className?: string
}

const iconTones: Record<Tone, string> = {
  neutral: 'bg-brand-100 text-brand-800',
  info: 'bg-info-100 text-info-700',
  success: 'bg-success-100 text-success-700',
  warning: 'bg-warning-100 text-warning-800',
  danger: 'bg-danger-100 text-danger-700',
  demo: 'bg-demo-100 text-demo-700',
}

/** KPI tile: label, one large figure, and a supporting line. */
export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = 'neutral',
  badge,
  onClick,
  loading = false,
  className,
}: StatCardProps) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          {icon && (
            <span
              aria-hidden="true"
              className={cx('grid size-8 shrink-0 place-items-center rounded-xl', iconTones[tone])}
            >
              {icon}
            </span>
          )}
          <span className="label-caps truncate">{label}</span>
        </div>
        {badge && <span className="shrink-0">{badge}</span>}
      </div>
      {loading ? (
        <Skeleton className="mt-4 h-9 w-16" />
      ) : (
        <p className="tabular mt-3 font-display text-[2.5rem] leading-none text-ink">{value}</p>
      )}
      {hint && <p className="mt-2 text-xs text-ink-soft">{hint}</p>}
    </>
  )
  const frame = cx(
    'block w-full rounded-2xl border border-line bg-surface p-5 text-left shadow-card',
    className,
  )
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={cx(frame, 'hc-lift hc-press cursor-pointer hover:border-brand-400/60')}
      >
        {body}
      </button>
    )
  }
  return <div className={frame}>{body}</div>
}
