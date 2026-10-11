import type { ReactNode } from 'react'
import { cx } from '../cx'
import { ErrorIcon, InboxIcon } from './icons'
import { Skeleton } from './Skeleton'

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const spinnerSizes = {
  sm: 'size-4',
  md: 'size-5',
  lg: 'size-8',
}

/** Decorative spinner. Pair it with visible or screen-reader text. */
export function Spinner({ size = 'md', className }: SpinnerProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={cx('animate-spin', spinnerSizes[size], className)}
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

interface StateFrameProps {
  icon: ReactNode
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  role?: 'status' | 'alert'
  className?: string
}

function StateFrame({ icon, title, description, action, role, className }: StateFrameProps) {
  return (
    <div
      role={role}
      className={cx(
        'flex flex-col items-center justify-center gap-2 px-6 py-12 text-center animate-(--animate-fade-in)',
        className,
      )}
    >
      {icon}
      <p className="mt-2 font-semibold text-ink">{title}</p>
      {description && <p className="max-w-md text-ink-soft">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}

function IconTile({ tone = 'brand', children }: { tone?: 'brand' | 'danger'; children: ReactNode }) {
  return (
    <span
      className={cx(
        'grid size-12 place-items-center rounded-2xl',
        tone === 'danger' ? 'bg-danger-100 text-danger-700' : 'bg-brand-100 text-brand-800',
      )}
    >
      {children}
    </span>
  )
}

export interface LoadingStateProps {
  label?: ReactNode
  /**
   * `spinner` (default) centres a spinner; `skeleton` sketches a page
   * (header, KPI row, card) while keeping the label for assistive technology.
   */
  variant?: 'spinner' | 'skeleton'
  className?: string
}

export function LoadingState({ label = 'Loading…', variant = 'spinner', className }: LoadingStateProps) {
  if (variant === 'skeleton') {
    return (
      <div role="status" className={cx('space-y-6', className)}>
        <span className="sr-only">{label}</span>
        <div className="space-y-3">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-9 w-72 max-w-full" />
          <Skeleton className="h-4 w-96 max-w-full" />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((n) => (
            <Skeleton key={n} className="h-32 rounded-2xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    )
  }
  return (
    <StateFrame
      role="status"
      icon={<Spinner size="lg" className="text-brand-600" />}
      title={label}
      className={className}
    />
  )
}

export interface EmptyStateProps {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}

export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <StateFrame
      icon={
        <IconTile>
          <InboxIcon className="size-6" />
        </IconTile>
      }
      title={title}
      description={description}
      action={action}
      className={className}
    />
  )
}

export interface ErrorStateProps {
  title?: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}

export function ErrorState({
  title = 'Something went wrong',
  description,
  action,
  className,
}: ErrorStateProps) {
  return (
    <StateFrame
      role="alert"
      icon={
        <IconTile tone="danger">
          <ErrorIcon className="size-6" />
        </IconTile>
      }
      title={title}
      description={description}
      action={action}
      className={className}
    />
  )
}
