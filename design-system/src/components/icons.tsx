import type { ReactNode } from 'react'
import type { Tone } from '../tone'

// Small inline icons so toned components never rely on colour alone.
// Internal to the design system; not exported from the package.

interface IconProps {
  className?: string
}

function Svg({ className, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  )
}

export function InfoIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="10" cy="10" r="7.25" />
      <path d="M10 9v4.5M10 6.5h.01" />
    </Svg>
  )
}

export function CheckIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="10" cy="10" r="7.25" />
      <path d="m7 10.25 2 2 4-4.5" />
    </Svg>
  )
}

export function WarningIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M8.7 3.5a1.5 1.5 0 0 1 2.6 0l5.5 9.75A1.5 1.5 0 0 1 15.5 15.5h-11a1.5 1.5 0 0 1-1.3-2.25z" />
      <path d="M10 8v3M10 13.25h.01" />
    </Svg>
  )
}

export function ErrorIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="10" cy="10" r="7.25" />
      <path d="m7.5 7.5 5 5m0-5-5 5" />
    </Svg>
  )
}

export function FlaskIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M8 3h4M8.75 3v4.5L4.6 14.6A1.25 1.25 0 0 0 5.7 16.5h8.6a1.25 1.25 0 0 0 1.1-1.9L11.25 7.5V3" />
      <path d="M6.5 12h7" />
    </Svg>
  )
}

export function InboxIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M3.5 11.5 5.6 5a1.5 1.5 0 0 1 1.4-1h6a1.5 1.5 0 0 1 1.4 1l2.1 6.5v3.5a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 3.5 15z" />
      <path d="M3.5 11.5h3.75l1 1.75h3.5l1-1.75h3.75" />
    </Svg>
  )
}

export function ToneIcon({ tone, className }: IconProps & { tone: Tone }) {
  switch (tone) {
    case 'success':
      return <CheckIcon className={className} />
    case 'warning':
      return <WarningIcon className={className} />
    case 'danger':
      return <ErrorIcon className={className} />
    case 'demo':
      return <FlaskIcon className={className} />
    default:
      return <InfoIcon className={className} />
  }
}

export function SunIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="10" cy="10" r="3.25" />
      <path d="M10 2.75v1.5M10 15.75v1.5M2.75 10h1.5M15.75 10h1.5M4.87 4.87l1.06 1.06M14.07 14.07l1.06 1.06M4.87 15.13l1.06-1.06M14.07 5.93l1.06-1.06" />
    </Svg>
  )
}

export function MoonIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M16.25 11.6A6.5 6.5 0 1 1 8.4 3.75a5.25 5.25 0 0 0 7.85 7.85Z" />
    </Svg>
  )
}

export function MonitorIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <rect x="2.75" y="3.75" width="14.5" height="9.5" rx="1.5" />
      <path d="M7.5 16.25h5M10 13.25v3" />
    </Svg>
  )
}

export function MenuIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M3.5 6h13M3.5 10h13M3.5 14h13" />
    </Svg>
  )
}

export function CloseIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="m5 5 10 10M15 5 5 15" />
    </Svg>
  )
}

export function ArrowRightIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M4 10h12M11 5l5 5-5 5" />
    </Svg>
  )
}
