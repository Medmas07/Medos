import type { MouseEventHandler, ReactNode } from 'react'
import { cx } from '../cx'
import { trackPointer } from '../pointer'
import type { Tone } from '../tone'
import { ArrowRightIcon } from './icons'
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
  /** Rendered under the figure, for example a status `Badge` or `DemoBadge`. */
  badge?: ReactNode
  /** Makes the whole tile a button (for example, to open the matching page). */
  onClick?: MouseEventHandler<HTMLButtonElement>
  /** Shows a skeleton in place of the value. */
  loading?: boolean
  id?: string
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

/**
 * KPI tile: label, one large figure, and a supporting line. Clickable tiles
 * get a cursor spotlight, a growing mint underline, and an arrow on hover.
 * Place several inside a `StatGroup` to render them as one segmented strip.
 */
export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = 'neutral',
  badge,
  onClick,
  loading = false,
  id,
  className,
}: StatCardProps) {
  const body = (
    <>
      <div className="flex min-w-0 items-center gap-2.5">
        {icon && (
          <span
            aria-hidden="true"
            className={cx('grid size-8 shrink-0 place-items-center rounded-xl', iconTones[tone])}
          >
            {icon}
          </span>
        )}
        <span className="label-caps min-w-0">{label}</span>
      </div>
      {loading ? (
        <Skeleton className="mt-4 h-10 w-16" />
      ) : (
        <p className="tabular mt-3 text-[2.75rem] leading-[1.05] font-semibold tracking-[-0.045em] text-ink">
          {value}
        </p>
      )}
      {hint && <p className="mt-2 text-xs leading-[1.125rem] text-ink-muted">{hint}</p>}
      {(badge || onClick) && (
        <div className="mt-3 flex min-h-6 items-center justify-between gap-3">
          {badge ?? <span />}
          {onClick && (
            <ArrowRightIcon className="size-4 shrink-0 -translate-x-1 text-brand-700 opacity-0 transition-[transform,opacity] duration-[260ms] ease-(--ease-out) group-hover/stat:translate-x-0 group-hover/stat:opacity-100" />
          )}
        </div>
      )}
    </>
  )
  const frame = cx('block w-full rounded-2xl border border-line bg-surface p-5 text-left', className)
  if (onClick) {
    return (
      <button
        id={id}
        type="button"
        onClick={onClick}
        onPointerMove={trackPointer}
        className={cx(frame, 'group/stat hc-spot hc-press cursor-pointer overflow-hidden')}
      >
        {body}
        <span
          aria-hidden="true"
          className="absolute inset-x-5 bottom-0 h-0.5 origin-left scale-x-0 rounded-full bg-brand-700 transition-transform duration-[320ms] ease-(--ease-out) group-hover/stat:scale-x-100"
        />
      </button>
    )
  }
  return (
    <div id={id} className={frame}>
      {body}
    </div>
  )
}

export interface StatGroupProps {
  /** Usually `StatCard`s. */
  children: ReactNode
  /** Columns at the widest breakpoint. */
  columns?: 2 | 3 | 4
  className?: string
}

const groupColumns = {
  2: 'sm:grid-cols-2',
  3: 'sm:grid-cols-3',
  4: 'sm:grid-cols-2 xl:grid-cols-4',
} as const

/** Renders `StatCard`s as one segmented strip with hairline dividers. */
export function StatGroup({ children, columns = 4, className }: StatGroupProps) {
  return (
    <div
      className={cx(
        'grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line',
        '[&>*]:rounded-none [&>*]:border-0',
        groupColumns[columns],
        className,
      )}
    >
      {children}
    </div>
  )
}
