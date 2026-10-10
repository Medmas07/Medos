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
  neutral: { frame: 'border-slate-200 bg-white', icon: 'text-slate-500' },
  info: { frame: 'border-info-200 bg-info-50', icon: 'text-info-600' },
  success: { frame: 'border-success-200 bg-success-50', icon: 'text-success-600' },
  warning: { frame: 'border-warning-200 bg-warning-50', icon: 'text-warning-600' },
  danger: { frame: 'border-danger-200 bg-danger-50', icon: 'text-danger-600' },
  demo: { frame: 'border-demo-200 bg-demo-50', icon: 'text-demo-600' },
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
      className={cx('flex gap-3 rounded-lg border p-4', styles.frame, className)}
    >
      <ToneIcon tone={tone} className={cx('mt-0.5 size-5 shrink-0', styles.icon)} />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-slate-900">{title}</p>
        {children && <div className="mt-1 text-slate-700">{children}</div>}
        {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  )
}
