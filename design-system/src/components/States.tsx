import type { ReactNode } from 'react'
import { cx } from '../cx'
import { ErrorIcon, InboxIcon } from './icons'

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
        'flex flex-col items-center justify-center gap-2 px-6 py-10 text-center',
        className,
      )}
    >
      {icon}
      <p className="font-semibold text-slate-900">{title}</p>
      {description && <p className="max-w-md text-slate-600">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export interface LoadingStateProps {
  label?: ReactNode
  className?: string
}

export function LoadingState({ label = 'Loading…', className }: LoadingStateProps) {
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
      icon={<InboxIcon className="size-8 text-slate-400" />}
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
      icon={<ErrorIcon className="size-8 text-danger-600" />}
      title={title}
      description={description}
      action={action}
      className={className}
    />
  )
}
