import type { ReactNode } from 'react'
import { cx } from '../cx'

export interface CardProps {
  title?: ReactNode
  description?: ReactNode
  /** Rendered at the top right of the header, for example a badge or button. */
  actions?: ReactNode
  footer?: ReactNode
  /** Removes body padding, for edge-to-edge content such as tables. */
  flush?: boolean
  /** Adds hover lift for cards that sit inside a link or button. */
  interactive?: boolean
  children?: ReactNode
  className?: string
}

export function Card({
  title,
  description,
  actions,
  footer,
  flush = false,
  interactive = false,
  children,
  className,
}: CardProps) {
  const hasHeader = title || description || actions
  return (
    <section
      className={cx(
        'rounded-2xl border border-line bg-surface shadow-card',
        interactive && 'hc-lift',
        className,
      )}
    >
      {hasHeader && (
        <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-base leading-6">{title}</h2>}
            {description && <p className="mt-0.5 text-ink-soft">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children && (
        <div
          className={cx(
            flush ? 'overflow-hidden' : 'px-5 py-4',
            flush && !hasHeader && 'rounded-t-2xl',
            flush && !footer && 'rounded-b-2xl',
          )}
        >
          {children}
        </div>
      )}
      {footer && (
        <footer className="rounded-b-2xl border-t border-line bg-surface-muted px-5 py-3">
          {footer}
        </footer>
      )}
    </section>
  )
}
