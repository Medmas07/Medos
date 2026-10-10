import type { ReactNode } from 'react'
import { cx } from '../cx'
import type { Tone } from '../tone'

export interface TimelineItem {
  id: string
  title: ReactNode
  /** Human-readable time, for example "10 Oct 2026, 14:05". */
  timestamp: string
  /** Machine-readable ISO 8601 value for the `<time>` element. */
  dateTime?: string
  description?: ReactNode
  /** Secondary details such as source organization or badges. */
  meta?: ReactNode
  tone?: Tone
  /** Emphasizes the in-progress step of a process. */
  current?: boolean
}

export interface TimelineProps {
  /** Accessible name for the list, for example "Request history". */
  label: string
  items: readonly TimelineItem[]
  className?: string
}

const markerTones: Record<Tone, string> = {
  neutral: 'bg-slate-400 ring-slate-100',
  info: 'bg-info-600 ring-info-100',
  success: 'bg-success-600 ring-success-100',
  warning: 'bg-warning-600 ring-warning-100',
  danger: 'bg-danger-600 ring-danger-100',
  demo: 'bg-demo-600 ring-demo-100',
}

/** Vertical, chronological list of events or process steps. */
export function Timeline({ label, items, className }: TimelineProps) {
  return (
    <ol aria-label={label} className={cx('relative', className)}>
      {items.map((item, index) => {
        const tone = item.tone ?? 'neutral'
        const isLast = index === items.length - 1
        return (
          <li
            key={item.id}
            aria-current={item.current ? 'step' : undefined}
            className="relative flex gap-4 pb-6 last:pb-0"
          >
            {!isLast && (
              <span aria-hidden="true" className="absolute top-4 left-[5px] h-full w-px bg-slate-200" />
            )}
            <span
              aria-hidden="true"
              className={cx(
                'relative mt-1.5 size-3 shrink-0 rounded-full ring-4',
                markerTones[tone],
                item.current && 'animate-pulse',
              )}
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <p className={cx('font-medium text-slate-900', item.current && 'font-semibold')}>
                  {item.title}
                </p>
                <time dateTime={item.dateTime} className="text-xs text-slate-500">
                  {item.timestamp}
                </time>
              </div>
              {item.description && <div className="mt-0.5 text-slate-600">{item.description}</div>}
              {item.meta && (
                <div className="mt-1.5 flex flex-wrap items-center gap-2">{item.meta}</div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
