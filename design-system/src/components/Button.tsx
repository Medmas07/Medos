import type { ButtonHTMLAttributes } from 'react'
import { cx } from '../cx'
import { Spinner } from './States'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  /** Disables the button and shows a spinner while an action is pending. */
  loading?: boolean
}

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-on-primary shadow-card hover:bg-primary-hover',
  secondary:
    'bg-surface text-ink shadow-card ring-1 ring-line-strong ring-inset hover:bg-brand-50 hover:ring-brand-400',
  ghost: 'text-ink-soft hover:bg-brand-50 hover:text-ink',
  danger: 'bg-danger-600 text-white shadow-card hover:bg-danger-800 dark:hover:bg-danger-200',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 gap-1.5 rounded-xl px-3 text-xs',
  md: 'h-11 gap-2 rounded-xl px-4 text-sm',
  lg: 'h-12 gap-2 rounded-2xl px-5 text-[15px]',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  type = 'button',
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cx(
        'hc-press inline-flex items-center justify-center font-medium whitespace-nowrap select-none',
        'transition-[background-color,color,box-shadow,transform] duration-150 ease-(--ease-out)',
        'disabled:pointer-events-none disabled:opacity-50',
        variants[variant],
        sizes[size],
        className,
      )}
      {...rest}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  )
}
