import type { ComponentProps } from 'react'
import type { LucideIcon } from 'lucide-react'

type Variant = 'primary' | 'glass' | 'mint' | 'ghost'
type Size = 'sm' | 'lg' | 'xl'

// Same pill shape and hover wipe as the design-system Button, for links.
const variants: Record<Variant, string> = {
  primary:
    'bg-primary text-on-primary shadow-card before:translate-y-[101%] before:bg-primary-wipe hover:text-on-mint hover:before:translate-y-0',
  glass: 'glass text-ink before:bg-white/40 before:opacity-0 hover:before:opacity-100',
  // Always mint on the always-dark brand panels.
  mint: 'bg-brand-300 text-on-mint before:bg-white/40 before:opacity-0 hover:before:opacity-100',
  ghost: 'text-ink-soft before:bg-surface-muted before:opacity-0 hover:text-ink hover:before:opacity-100',
}

const sizes: Record<Size, string> = {
  sm: 'h-9 gap-1.5 px-4 text-[13px]',
  lg: 'h-12 gap-2 px-6 text-[15px]',
  xl: 'h-14 gap-2 px-7 text-base',
}

interface LinkButtonProps extends ComponentProps<'a'> {
  variant?: Variant
  size?: Size
  icon?: LucideIcon
  iconRight?: LucideIcon
}

export function LinkButton({ variant = 'primary', size = 'lg', icon: Icon, iconRight: IconRight, className = '', children, ...rest }: LinkButtonProps) {
  return (
    <a
      className={[
        'hc-press relative isolate inline-flex items-center justify-center overflow-hidden rounded-full font-semibold whitespace-nowrap select-none',
        'transition-[color,box-shadow,transform] duration-200 ease-(--ease-out)',
        "before:absolute before:inset-0 before:-z-10 before:rounded-[inherit] before:content-['']",
        'before:transition-[transform,opacity] before:duration-[260ms] before:ease-(--ease-out)',
        variants[variant],
        sizes[size],
        className,
      ].join(' ')}
      {...rest}
    >
      {Icon && <Icon aria-hidden className="size-4" strokeWidth={1.9} />}
      {children}
      {IconRight && <IconRight aria-hidden className="size-4" strokeWidth={1.9} />}
    </a>
  )
}
