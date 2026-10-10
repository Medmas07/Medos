import { useId } from 'react'
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'
import { cx } from '../cx'

interface FieldBaseProps {
  label: ReactNode
  hint?: ReactNode
  /** Validation message; also marks the control as invalid. */
  error?: ReactNode
}

const controlBase =
  'block w-full rounded-md border bg-white px-3 text-sm text-slate-900 shadow-xs placeholder:text-slate-400 ' +
  'focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20 focus:outline-none ' +
  'disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500'

function controlState(error: ReactNode) {
  return error ? 'border-danger-600' : 'border-slate-300'
}

/** Wires label, hint, and error ids to one control. */
function useFieldIds(id: string | undefined, hint: ReactNode, error: ReactNode) {
  const generated = useId()
  const controlId = id ?? generated
  const hintId = hint ? `${controlId}-hint` : undefined
  const errorId = error ? `${controlId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined
  return { controlId, hintId, errorId, describedBy }
}

interface FieldShellProps extends FieldBaseProps {
  controlId: string
  hintId?: string
  errorId?: string
  required?: boolean
  children: ReactNode
}

function FieldShell({
  label,
  hint,
  error,
  controlId,
  hintId,
  errorId,
  required,
  children,
}: FieldShellProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={controlId} className="block font-medium text-slate-800">
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-danger-700">
            *
          </span>
        )}
      </label>
      {children}
      {hint && (
        <p id={hintId} className="text-xs text-slate-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs font-medium text-danger-700">
          {error}
        </p>
      )}
    </div>
  )
}

export interface TextFieldProps extends FieldBaseProps, InputHTMLAttributes<HTMLInputElement> {}

export function TextField({ label, hint, error, id, className, ...input }: TextFieldProps) {
  const ids = useFieldIds(id, hint, error)
  return (
    <FieldShell label={label} hint={hint} error={error} required={input.required} {...ids}>
      <input
        id={ids.controlId}
        aria-describedby={ids.describedBy}
        aria-invalid={error ? true : undefined}
        className={cx(controlBase, 'h-10', controlState(error), className)}
        {...input}
      />
    </FieldShell>
  )
}

export interface TextareaFieldProps
  extends FieldBaseProps, TextareaHTMLAttributes<HTMLTextAreaElement> {}

export function TextareaField({
  label,
  hint,
  error,
  id,
  className,
  rows = 4,
  ...textarea
}: TextareaFieldProps) {
  const ids = useFieldIds(id, hint, error)
  return (
    <FieldShell label={label} hint={hint} error={error} required={textarea.required} {...ids}>
      <textarea
        id={ids.controlId}
        rows={rows}
        aria-describedby={ids.describedBy}
        aria-invalid={error ? true : undefined}
        className={cx(controlBase, 'py-2', controlState(error), className)}
        {...textarea}
      />
    </FieldShell>
  )
}

export interface SelectOption {
  value: string
  label: string
}

export interface SelectFieldProps extends FieldBaseProps, SelectHTMLAttributes<HTMLSelectElement> {
  options: readonly SelectOption[]
  /** Adds an empty first option with this label. */
  placeholder?: string
}

export function SelectField({
  label,
  hint,
  error,
  id,
  className,
  options,
  placeholder,
  ...select
}: SelectFieldProps) {
  const ids = useFieldIds(id, hint, error)
  return (
    <FieldShell label={label} hint={hint} error={error} required={select.required} {...ids}>
      <select
        id={ids.controlId}
        aria-describedby={ids.describedBy}
        aria-invalid={error ? true : undefined}
        className={cx(controlBase, 'h-10 pr-8', controlState(error), className)}
        {...select}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  )
}

export interface CheckboxFieldProps
  extends FieldBaseProps, Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {}

export function CheckboxField({ label, hint, error, id, className, ...input }: CheckboxFieldProps) {
  const ids = useFieldIds(id, hint, error)
  return (
    <div className={cx('flex gap-3', className)}>
      <input
        type="checkbox"
        id={ids.controlId}
        aria-describedby={ids.describedBy}
        aria-invalid={error ? true : undefined}
        className="mt-1 size-4 shrink-0 rounded border-slate-300 accent-brand-700"
        {...input}
      />
      <div className="space-y-0.5">
        <label htmlFor={ids.controlId} className="font-medium text-slate-800">
          {label}
        </label>
        {hint && (
          <p id={ids.hintId} className="text-xs text-slate-500">
            {hint}
          </p>
        )}
        {error && (
          <p id={ids.errorId} className="text-xs font-medium text-danger-700">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
