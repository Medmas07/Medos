import { ThemeToggle } from '@hackcure/design-system'
import { copy } from './copy'
import { LinkButton } from './LinkButton'
import { JOURNEY_START_HREF, SIGN_IN_HREF } from './links'
import { Logo } from './Logo'

export function SiteNav() {
  return (
    <header className="intro-hide fixed inset-x-0 top-0 z-40 px-3 pt-[env(safe-area-inset-top)] sm:px-6" style={{ ['--i' as string]: 0 }}>
      <nav
        aria-label="Navigation principale"
        className="glass-chrome mx-auto mt-3 flex h-14 max-w-[1320px] items-center justify-between gap-4 rounded-2xl px-3 shadow-card sm:px-4"
      >
        <a href="#" aria-label={`${copy.brand}, accueil`} className="rounded-lg">
          <Logo />
        </a>
        <ul className="hidden items-center gap-1 text-sm font-medium text-ink-soft md:flex">
          <li><a href="#fonctionnement" className="rounded-lg px-3 py-2 transition-colors hover:text-ink">{copy.nav.how}</a></li>
          <li><a href="#ecosysteme" className="rounded-lg px-3 py-2 transition-colors hover:text-ink">{copy.nav.ecosystem}</a></li>
          <li><a href="#confiance" className="rounded-lg px-3 py-2 transition-colors hover:text-ink">{copy.nav.trust}</a></li>
          <li><a href="#etablissements" className="rounded-lg px-3 py-2 transition-colors hover:text-ink">{copy.nav.hospitals}</a></li>
        </ul>
        <div className="flex items-center gap-1.5">
          <LinkButton href={SIGN_IN_HREF} variant="ghost" size="sm">
            {copy.nav.signIn}
          </LinkButton>
          <LinkButton href={JOURNEY_START_HREF} size="sm" className="max-sm:hidden">
            {copy.nav.cta}
          </LinkButton>
          <ThemeToggle />
        </div>
      </nav>
    </header>
  )
}
