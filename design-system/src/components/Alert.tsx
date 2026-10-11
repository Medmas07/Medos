import type { ReactNode } from 'react'
import { cx } from '../cx'
import type { Tone } from '../tone'
import { ToneIcon } from './icons'

export interface AlertProps {
  tone?: Tone
  title: ReactNode
  children?: ReactNode
  /** Optional actions rendered under the message, such as buttons. */
  actions?: ReactNode
  className?: string
}

const alertTones: Record<Tone, { frame: string; icon: string }> = {
  neutral: { frame: 'border-line bg-surface', icon: 'bg-surface-muted text-ink-muted' },
  info: { frame: 'border-info-200 bg-info-50', icon: 'bg-info-100 text-info-700' },
  success: { frame: 'border-success-200 bg-success-50', icon: 'bg-success-100 text-success-700' },
  warning: { frame: 'border-warning-200 bg-warning-50', icon: 'bg-warning-100 text-warning-700' },
  danger: { frame: 'border-danger-200 bg-danger-50', icon: 'bg-danger-100 text-danger-700' },
  demo: { frame: 'border-demo-200 bg-demo-50', icon: 'bg-demo-100 text-demo-700' },
}

/**
 * Inline message. Warning and danger alerts are announced immediately
 * (`role="alert"`); other tones are polite (`role="status"`).
 */
export function Alert({ tone = 'info', title, children, actions, className }: AlertProps) {
  const styles = alertTones[tone]
  return (
    <div
      role={tone === 'warning' || tone === 'danger' ? 'alert' : 'status'}
      className={cx('flex gap-3 rounded-2xl border p-4', styles.frame, className)}
    >
      <span className={cx('grid size-8 shrink-0 place-items-center rounded-xl', styles.icon)}>
        <ToneIcon tone={tone} className="size-[18px]" />
      </span>
      <div className="min-w-0 flex-1 pt-1">
        <p className="font-semibold text-ink">{title}</p>
        {children && <div className="mt-1 text-ink-soft">{children}</div>}
        {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  )
}
