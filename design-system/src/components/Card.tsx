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
  children?: ReactNode
  className?: string
}

export function Card({
  title,
  description,
  actions,
  footer,
  flush = false,
  children,
  className,
}: CardProps) {
  const hasHeader = title || description || actions
  return (
    <section
      className={cx(
        'overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xs',
        className,
      )}
    >
      {hasHeader && (
        <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3 border-b border-slate-200 px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-base leading-6">{title}</h2>}
            {description && <p className="mt-0.5 text-slate-600">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      {children && <div className={flush ? undefined : 'px-5 py-4'}>{children}</div>}
      {footer && (
        <footer className="border-t border-slate-200 bg-slate-50 px-5 py-3">{footer}</footer>
      )}
    </section>
  )
}
