/** Wordmark + mark: three hospital nodes stacked into one federated network. */
export function Logo({ tone = 'ink', className = '' }: { tone?: 'ink' | 'light'; className?: string }) {
  const ink = tone === 'ink'
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg viewBox="0 0 28 28" aria-hidden className="size-7 shrink-0">
        <rect x="3" y="9" width="15" height="16" rx="4" className={ink ? 'fill-brand-300' : 'fill-brand-300/60'} />
        <rect x="7" y="6" width="15" height="16" rx="4" className={ink ? 'fill-brand-500' : 'fill-brand-300/80'} />
        <rect x="11" y="3" width="15" height="16" rx="4" className={ink ? 'fill-brand-700' : 'fill-white'} />
      </svg>
      <span className={`text-[22px] leading-none font-semibold tracking-[-0.035em] ${ink ? 'text-ink' : 'text-white'}`}>
        medos
      </span>
    </span>
  )
}
