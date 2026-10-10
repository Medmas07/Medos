import type { MouseEventHandler, ReactNode } from 'react'
import { cx } from '../cx'

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
  children: ReactNode
}

/** Page frame shared by the portals: sidebar navigation beside the main content. */
export function AppShell({
  productName,
  productContext,
  navigation,
  banner,
  sidebarFooter,
  children,
}: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col md:h-screen">
      {banner}
      <div className="flex flex-1 flex-col md:min-h-0 md:flex-row">
        <aside className="flex shrink-0 flex-col border-b border-slate-200 bg-white md:w-64 md:overflow-y-auto md:border-r md:border-b-0">
          <div className="px-5 py-4">
            <p className="font-semibold text-slate-900">{productName}</p>
            {productContext && <p className="text-xs text-slate-500">{productContext}</p>}
          </div>
          <div className="flex-1 px-3 pb-4">{navigation}</div>
          {sidebarFooter && (
            <div className="border-t border-slate-200 px-5 py-3 text-xs text-slate-600">
              {sidebarFooter}
            </div>
          )}
        </aside>
        <main className="min-w-0 flex-1 px-4 py-6 md:overflow-y-auto md:px-8">{children}</main>
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
    <nav aria-label={label} className="space-y-5">
      {sections.map((section, index) => (
        <div key={section.title ?? index}>
          {section.title && <h4 className="mb-1 px-2">{section.title}</h4>}
          <ul className="space-y-0.5">
            {section.items.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  onClick={item.onClick}
                  aria-current={item.current ? 'page' : undefined}
                  className={cx(
                    'flex items-center justify-between gap-2 rounded-md px-2 py-1.5 font-medium transition-colors',
                    item.current
                      ? 'bg-brand-50 text-brand-800'
                      : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900',
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
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1 text-xs font-medium text-brand-700">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-slate-600">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  )
}
