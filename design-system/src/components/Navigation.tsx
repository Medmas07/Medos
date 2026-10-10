import { useRef } from 'react'
import type { MouseEvent, MouseEventHandler, ReactNode } from 'react'
import { cx } from '../cx'
import { CloseIcon, MenuIcon } from './icons'

export interface AppShellProps {
  /** Product name shown at the top of the sidebar, for example "Governance Portal". */
  productName: ReactNode
  /** Short line under the product name, for example the acting organization. */
  productContext?: ReactNode
  /** Usually a `SideNav`. */
  navigation: ReactNode
  /** Full-width content above the layout, usually a `DemoBanner`. */
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

function BrandMark() {
  return (
    <span
      aria-hidden="true"
      className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-300 text-brand-950 shadow-[inset_0_1px_0_rgb(255_255_255/0.5)]"
    >
      <svg viewBox="0 0 20 20" className="size-5" fill="none" stroke="currentColor" strokeWidth={2.25} strokeLinecap="round">
        <path d="M10 4.5v11M4.5 10h11" />
      </svg>
    </span>
  )
}

function Brand({ productName, productContext }: Pick<AppShellProps, 'productName' | 'productContext'>) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <BrandMark />
      <div className="min-w-0">
        <p className="truncate font-semibold text-ink">{productName}</p>
        {productContext && <p className="truncate text-xs text-ink-muted">{productContext}</p>}
      </div>
    </div>
  )
}

/**
 * Page frame shared by the portals: a dark mint sidebar beside the content on
 * large screens; a top bar with a navigation drawer on small screens.
 */
export function AppShell({
  productName,
  productContext,
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

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      {banner}
      <div className="flex flex-1 flex-col lg:min-h-0 lg:flex-row">
        {/* Desktop sidebar */}
        <aside className="hc-chrome hidden w-[264px] shrink-0 flex-col border-r border-line/60 bg-chrome text-ink lg:flex">
          <div className="px-5 pt-5 pb-6">
            <Brand productName={productName} productContext={productContext} />
          </div>
          <div className="flex-1 overflow-y-auto px-3 pb-4">{navigation}</div>
          {(sidebarFooter || toolbar) && (
            <div className="space-y-3 border-t border-line/70 p-3">
              {sidebarFooter && (
                <div className="rounded-2xl bg-surface-muted/60 px-3 py-2.5 text-xs text-ink-soft">
                  {sidebarFooter}
                </div>
              )}
              {toolbar && <div className="flex items-center justify-between gap-2 px-1">{toolbar}</div>}
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
            className="hc-press grid size-11 shrink-0 place-items-center rounded-xl text-ink-soft hover:bg-brand-50 hover:text-ink"
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
          className="hc-drawer hc-chrome bg-chrome text-ink lg:hidden"
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-5">
              <Brand productName={productName} productContext={productContext} />
              <button
                type="button"
                aria-label="Fermer la navigation"
                onClick={closeDrawer}
                className="hc-press grid size-11 shrink-0 place-items-center rounded-xl text-ink-soft hover:bg-surface-muted hover:text-ink"
              >
                <CloseIcon className="size-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 pb-4">{navigation}</div>
            {sidebarFooter && (
              <div className="border-t border-line/70 p-3">
                <div className="rounded-2xl bg-surface-muted/60 px-3 py-2.5 text-xs text-ink-soft">
                  {sidebarFooter}
                </div>
              </div>
            )}
          </div>
        </dialog>

        <main className="min-w-0 flex-1 lg:overflow-y-auto">
          <div
            key={pageKey}
            className="mx-auto w-full max-w-6xl px-4 pt-6 pb-16 animate-(--animate-page) sm:px-6 lg:px-10 lg:pt-10"
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

/**
 * Vertical navigation list. Items are plain links; portals that adopt a
 * client-side router can pass `onClick` to intercept navigation.
 */
export function SideNav({ label, sections }: SideNavProps) {
  return (
    <nav aria-label={label} className="space-y-6">
      {sections.map((section, index) => (
        <div key={section.title ?? index}>
          {section.title && <h4 className="mb-1.5 px-3">{section.title}</h4>}
          <ul className="space-y-0.5">
            {section.items.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  onClick={item.onClick}
                  aria-current={item.current ? 'page' : undefined}
                  className={cx(
                    'relative flex min-h-10 items-center justify-between gap-2 rounded-xl px-3 py-2 font-medium transition-colors duration-150',
                    item.current
                      ? 'bg-brand-300/15 text-ink before:absolute before:inset-y-2 before:left-0 before:w-[3px] before:rounded-full before:bg-brand-300'
                      : 'text-ink-soft hover:bg-surface-muted/70 hover:text-ink',
                  )}
                >
                  <span className="truncate">{item.label}</span>
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
    <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="label-caps mb-2 text-brand-700!">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p className="mt-2 max-w-[65ch] text-[15px] text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2 sm:max-w-[60%] sm:justify-end">{actions}</div>}
    </header>
  )
}
