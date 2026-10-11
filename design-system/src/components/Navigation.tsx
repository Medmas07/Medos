import { useLayoutEffect, useRef, useState } from 'react'
import type { MouseEvent, MouseEventHandler, ReactNode } from 'react'
import { cx } from '../cx'
import { CloseIcon, MenuIcon } from './icons'

export interface AppShellProps {
  /** Product name shown at the top of the sidebar, for example "Governance Portal". */
  productName: ReactNode
  /** Short line under the product name, for example the acting organization. */
  productContext?: ReactNode
  /**
   * One or two characters for the brand mark. Defaults to the first letter
   * of the last word of `productName` when it is a string.
   */
  productMark?: ReactNode
  /** Usually a `SideNav`. */
  navigation: ReactNode
  /** Full-width content above the layout. */
  banner?: ReactNode
  /** Content pinned to the bottom of the sidebar, for example the signed-in identity. */
  sidebarFooter?: ReactNode
  /**
   * Compact tools such as a `ThemeToggle`: shown in the sidebar on desktop and
   * in the top bar on small screens.
   */
  toolbar?: ReactNode
  /**
   * Identifies the current page. When it changes, the content plays a short
   * entrance transition.
   */
  pageKey?: string
  children: ReactNode
}

function defaultMark(productName: ReactNode) {
  if (typeof productName !== 'string') return null
  const words = productName.trim().split(/\s+/)
  return words[words.length - 1]?.charAt(0).toUpperCase() ?? null
}

function Brand({
  productName,
  productContext,
  productMark,
}: Pick<AppShellProps, 'productName' | 'productContext' | 'productMark'>) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span
        aria-hidden="true"
        className="grid size-9 shrink-0 place-items-center rounded-[11px] bg-brand-300 text-[15px] font-bold tracking-[-0.04em] text-on-mint"
      >
        {productMark ?? defaultMark(productName)}
      </span>
      <div className="min-w-0">
        <p className="truncate text-[15px] leading-5 font-semibold tracking-[-0.01em] text-ink">
          {productName}
        </p>
        {productContext && <p className="truncate text-xs text-ink-muted">{productContext}</p>}
      </div>
    </div>
  )
}

/**
 * Page frame shared by the portals: navigation on the paper background and
 * the page on a rounded canvas (large screens); a top bar with a navigation
 * drawer on small screens.
 */
export function AppShell({
  productName,
  productContext,
  productMark,
  navigation,
  banner,
  sidebarFooter,
  toolbar,
  pageKey,
  children,
}: AppShellProps) {
  const drawer = useRef<HTMLDialogElement>(null)
  const closeDrawer = () => drawer.current?.close()

  // Close after choosing a link, or when the backdrop (the dialog itself) is clicked.
  const onDrawerClick = (event: MouseEvent<HTMLDialogElement>) => {
    const target = event.target as HTMLElement
    if (target === event.currentTarget || target.closest('a')) closeDrawer()
  }

  const brand = <Brand productName={productName} productContext={productContext} productMark={productMark} />
  const identity = sidebarFooter && (
    <div className="rounded-2xl border border-line bg-surface px-3 py-2.5 text-xs text-ink-soft">
      {sidebarFooter}
    </div>
  )

  return (
    <div className="flex min-h-dvh flex-col bg-paper lg:h-dvh">
      {banner}
      <div className="flex flex-1 flex-col lg:min-h-0 lg:flex-row lg:gap-3 lg:p-3">
        {/* Desktop sidebar */}
        <aside className="hidden w-[252px] shrink-0 flex-col lg:flex">
          <div className="px-3 pt-2.5 pb-7">{brand}</div>
          <div className="flex-1 overflow-y-auto px-1 pb-4">{navigation}</div>
          {(identity || toolbar) && (
            <div className="space-y-3 px-1 pt-3">
              {identity}
              {toolbar && <div className="flex items-center gap-2">{toolbar}</div>}
            </div>
          )}
        </aside>

        {/* Mobile top bar */}
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-line bg-paper/85 px-2 backdrop-blur-md lg:hidden">
          <button
            type="button"
            aria-label="Ouvrir la navigation"
            title="Navigation"
            onClick={() => drawer.current?.showModal()}
            className="hc-press grid size-11 shrink-0 place-items-center rounded-full text-ink-soft transition-colors hover:bg-surface-muted hover:text-ink"
          >
            <MenuIcon className="size-5" />
          </button>
          <p className="min-w-0 flex-1 truncate font-semibold text-ink">{productName}</p>
          {toolbar}
        </header>

        {/* Mobile navigation drawer */}
        <dialog
          ref={drawer}
          aria-label="Navigation"
          onClick={onDrawerClick}
          className="hc-drawer bg-paper text-ink lg:hidden"
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-6">
              {brand}
              <button
                type="button"
                aria-label="Fermer la navigation"
                onClick={closeDrawer}
                className="hc-press grid size-11 shrink-0 place-items-center rounded-full text-ink-soft transition-colors hover:bg-surface-muted hover:text-ink"
              >
                <CloseIcon className="size-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-4">{navigation}</div>
            {identity && <div className="p-3">{identity}</div>}
          </div>
        </dialog>

        <main className="min-w-0 flex-1 bg-surface lg:overflow-y-auto lg:rounded-[1.5rem] lg:border lg:border-line">
          <div
            key={pageKey}
            className="mx-auto w-full max-w-6xl px-4 pt-6 pb-16 animate-(--animate-page) sm:px-8 lg:px-12 lg:pt-10"
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export interface SideNavItem {
  label: ReactNode
  href: string
  current?: boolean
  /** Trailing content such as a count `Badge`. */
  badge?: ReactNode
  onClick?: MouseEventHandler<HTMLAnchorElement>
}

export interface SideNavSection {
  /** Optional group heading. */
  title?: string
  items: readonly SideNavItem[]
}

export interface SideNavProps {
  /** Accessible name, for example "Main". */
  label: string
  sections: readonly SideNavSection[]
}

interface Indicator {
  top: number
  height: number
}

/**
 * Vertical navigation list. One mint indicator glides to the current item.
 * Items are plain links; portals that adopt a client-side router can pass
 * `onClick` to intercept navigation.
 */
export function SideNav({ label, sections }: SideNavProps) {
  const nav = useRef<HTMLElement>(null)
  const pill = useRef<HTMLSpanElement>(null)
  const [indicator, setIndicator] = useState<Indicator | null>(null)
  // The first placement must not slide in from the top of the list.
  const [animate, setAnimate] = useState(false)

  useLayoutEffect(() => {
    const measure = () => {
      const active = nav.current?.querySelector<HTMLElement>('a[aria-current="page"]')
      setIndicator((previous) => {
        if (!active) return null
        const next = { top: active.offsetTop, height: active.offsetHeight }
        return previous && previous.top === next.top && previous.height === next.height ? previous : next
      })
    }
    measure()
    const observer = new ResizeObserver(measure)
    if (nav.current) observer.observe(nav.current)
    return () => observer.disconnect()
  })

  useLayoutEffect(() => {
    if (indicator && !animate) {
      const frame = requestAnimationFrame(() => setAnimate(true))
      return () => cancelAnimationFrame(frame)
    }
  }, [indicator, animate])

  return (
    <nav ref={nav} aria-label={label} className="relative space-y-6">
      {indicator && (
        <span
          ref={pill}
          aria-hidden="true"
          className={cx(
            'pointer-events-none absolute inset-x-0 top-0 rounded-xl bg-brand-300',
            animate && 'transition-transform duration-300 ease-(--ease-drawer)',
          )}
          style={{ height: indicator.height, transform: `translateY(${indicator.top}px)` }}
        />
      )}
      {sections.map((section, index) => (
        <div key={section.title ?? index}>
          {section.title && <h4 className="mb-1.5 px-3">{section.title}</h4>}
          <ul className="space-y-0.5">
            {section.items.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  onClick={(event) => {
                    // Start the glide on click, before the page re-renders.
                    const link = event.currentTarget
                    if (pill.current) pill.current.style.transform = `translateY(${link.offsetTop}px)`
                    item.onClick?.(event)
                  }}
                  aria-current={item.current ? 'page' : undefined}
                  className={cx(
                    'group/nav relative flex min-h-10 items-center justify-between gap-2 rounded-xl px-3 py-2 transition-colors duration-200',
                    item.current
                      ? 'font-semibold text-on-mint'
                      : 'font-medium text-ink-soft hover:bg-surface-muted hover:text-ink',
                  )}
                >
                  <span
                    className={cx(
                      'truncate transition-transform duration-200 ease-(--ease-out)',
                      !item.current && 'group-hover/nav:translate-x-0.5',
                    )}
                  >
                    {item.label}
                  </span>
                  {item.badge}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  )
}

export interface PageHeaderProps {
  title: ReactNode
  description?: ReactNode
  /** Small line above the title, for example a breadcrumb or section name. */
  eyebrow?: ReactNode
  /** Page-level actions aligned to the right. */
  actions?: ReactNode
}

export function PageHeader({ title, description, eyebrow, actions }: PageHeaderProps) {
  return (
    <header className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-2.5 text-[13px] font-medium text-ink-muted">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p className="mt-3 max-w-[62ch] text-[15px] leading-[1.55] text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex min-w-0 flex-wrap gap-2 sm:max-w-[60%] sm:justify-end">{actions}</div>}
    </header>
  )
}
