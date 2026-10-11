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

// Hover layers live on ::before (behind the label) and move only by transform or opacity.
const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-on-primary shadow-card before:translate-y-[101%] before:bg-primary-wipe hover:text-on-mint hover:before:translate-y-0',
  secondary:
    'bg-surface text-ink ring-1 ring-line-strong ring-inset before:bg-brand-50 before:opacity-0 hover:ring-brand-700/50 hover:before:opacity-100',
  ghost: 'text-ink-soft before:bg-surface-muted before:opacity-0 hover:text-ink hover:before:opacity-100',
  danger: 'bg-danger-600 text-white shadow-card before:bg-black/15 before:opacity-0 hover:before:opacity-100',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 gap-1.5 px-4 text-[13px]',
  md: 'h-11 gap-2 px-5 text-sm',
  lg: 'h-12 gap-2 px-6 text-[15px]',
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
        'hc-press relative isolate inline-flex items-center justify-center overflow-hidden rounded-full font-semibold whitespace-nowrap select-none',
        'transition-[color,box-shadow,transform] duration-200 ease-(--ease-out)',
        "before:absolute before:inset-0 before:-z-10 before:rounded-[inherit] before:content-['']",
        'before:transition-[transform,opacity] before:duration-[260ms] before:ease-(--ease-out)',
        '[&>svg]:transition-transform [&>svg]:duration-200 hover:[&>svg:last-child]:translate-x-[3px]',
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
