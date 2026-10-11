import {
  Bot,
  Building2,
  Database,
  Download,
  FlaskConical,
  Fingerprint,
  KeyRound,
  Landmark,
  ShieldCheck,
  Smartphone,
  UserRoundCheck,
} from 'lucide-react'
import { copy } from './copy'
import { LinkButton } from './LinkButton'
import { JOURNEY_START_HREF, SIGN_IN_HREF } from './links'
import { Logo } from './Logo'
import { Reveal } from './Reveal'

const wrap = 'mx-auto w-full max-w-[1320px] px-4 sm:px-8 lg:px-12'
const sectionTitle = 'text-[clamp(2.4rem,4.6vw,4rem)] leading-[1.04] font-semibold tracking-[-0.045em] text-ink'

/* ---------------- Ecosystem: 5 actors, 5 cells, mixed sizes and backgrounds ---------------- */

export function Features() {
  const f = copy.features
  return (
    <section id="ecosysteme" aria-labelledby="features-title" className="relative py-24 sm:py-32">
      <div className={wrap}>
        <Reveal as="header" className="max-w-[44rem]">
          <h2 id="features-title" className={sectionTitle}>
            {f.title}
          </h2>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-12">
          {/* 1. Hospital Nodes: large, with two fictional node cards */}
          <Reveal className="lg:col-span-7 lg:row-span-2">
            <article className="relative flex h-full min-h-[26rem] flex-col overflow-hidden rounded-3xl bg-gradient-to-br from-brand-100 via-brand-50 to-surface p-6 sm:p-8">
              <CellText title={f.nodes.title} body={f.nodes.body} icon={Building2} />
              <div className="relative mt-8 flex-1" aria-hidden>
                <NodeCard
                  name="Hôpital Universitaire Bab Ennour"
                  node="node-hospital-a"
                  status="En ligne"
                  className="absolute top-0 left-[4%] w-[min(100%,21rem)] -rotate-2 opacity-80"
                />
                <NodeCard
                  name="Centre Hospitalier Cap Azur"
                  node="node-hospital-c"
                  status="Configuration"
                  className="relative top-14 left-[14%] w-[min(100%,21rem)] rotate-1 shadow-lift sm:left-[30%]"
                />
              </div>
            </article>
          </Reveal>

          {/* 2. Governance: deep teal cell */}
          <Reveal className="lg:col-span-5">
            <article className="flex h-full flex-col justify-between gap-8 rounded-3xl bg-brand-950 p-6 text-white sm:p-8">
              <div>
                <Landmark aria-hidden className="size-6 text-brand-300" strokeWidth={1.5} />
                <h3 className="mt-5 text-xl font-semibold text-white">{f.governance.title}</h3>
                <p className="mt-2 max-w-[38ch] text-[15px] leading-relaxed text-white/70">{f.governance.body}</p>
              </div>
              <div className="grid grid-cols-4 gap-1 rounded-2xl bg-white/8 p-1" aria-hidden>
                {f.governance.chips.map((x, i) => (
                  <span
                    key={x}
                    className={`grid h-10 place-items-center rounded-xl text-sm font-medium ${i === 1 ? 'bg-brand-300 text-on-mint' : 'text-white/75'}`}
                  >
                    {x}
                  </span>
                ))}
              </div>
            </article>
          </Reveal>

          {/* 3. Research compute-to-data */}
          <Reveal className="lg:col-span-5">
            <article className="flex h-full flex-col gap-6 rounded-3xl border border-line bg-surface p-6 sm:p-8">
              <CellText title={f.research.title} body={f.research.body} icon={FlaskConical} />
              <ul className="space-y-2.5" aria-hidden>
                {[
                  { label: 'Projet R-12 · Exécution autorisée', meta: 'Hôpital A', tone: 'bg-success-600' },
                  { label: 'Résultat agrégé · Contrôle de sortie', meta: 'Validé', tone: 'bg-brand-500' },
                ].map((row) => (
                  <li key={row.label} className="flex items-center gap-3 rounded-2xl bg-surface-muted px-3 py-2.5">
                    <span className={`size-2 shrink-0 rounded-full ${row.tone}`} />
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{row.label}</span>
                    <span className="shrink-0 text-xs text-ink-muted">{row.meta}</span>
                  </li>
                ))}
              </ul>
            </article>
          </Reveal>

          {/* 4. AI that assists */}
          <Reveal className="lg:col-span-6">
            <article className="flex h-full flex-col gap-6 rounded-3xl border border-line bg-surface p-6 sm:p-8">
              <CellText title={f.ai.title} body={f.ai.body} icon={Bot} />
              <ol className="relative ml-2 space-y-4 border-l border-line-strong pl-6" aria-hidden>
                {[
                  { icon: Bot, label: 'Suggestion IA · indicative', meta: 'Extraction de compte rendu' },
                  { icon: UserRoundCheck, label: 'Revue du clinicien', meta: 'Validation humaine requise' },
                  { icon: ShieldCheck, label: 'Donnée confirmée', meta: 'Après validation uniquement' },
                ].map((row) => (
                  <li key={row.label} className="relative">
                    <span className="absolute -left-[37px] grid size-6 place-items-center rounded-full bg-brand-100 text-brand-800 ring-4 ring-surface">
                      <row.icon className="size-3.5" strokeWidth={2} />
                    </span>
                    <p className="text-sm font-medium text-ink">{row.label}</p>
                    <p className="text-xs text-ink-muted">{row.meta}</p>
                  </li>
                ))}
              </ol>
            </article>
          </Reveal>

          {/* 5. Patient and clinician apps: always-mint cell */}
          <Reveal className="md:col-span-2 lg:col-span-6">
            <article className="relative flex h-full flex-col justify-between gap-8 overflow-hidden rounded-3xl bg-gradient-to-br from-brand-300 via-[#c3eae0] to-[#def2ed] p-6 text-on-mint sm:p-8">
              <div>
                <Smartphone aria-hidden className="mb-5 size-6 text-brand-950" strokeWidth={1.5} />
                <h3 className="text-xl font-semibold text-on-mint">{f.apps.title}</h3>
                <p className="mt-2 max-w-[40ch] text-[15px] leading-relaxed text-brand-950/80">{f.apps.body}</p>
              </div>
              <div className="flex items-center gap-3 self-start rounded-2xl border border-white/70 bg-white/60 p-3 pr-5 backdrop-blur" aria-hidden>
                <span className="grid size-10 place-items-center rounded-xl bg-brand-950 text-white">
                  <KeyRound className="size-5" strokeWidth={1.75} />
                </span>
                <span>
                  <span className="block text-sm font-semibold text-brand-950">Accès accordé · Cardiologie</span>
                  <span className="block text-xs text-brand-950/75">Autorisé par le patient, expire dans 7 jours</span>
                </span>
              </div>
            </article>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

function NodeCard({ name, node, status, className }: { name: string; node: string; status: string; className: string }) {
  const online = status === 'En ligne'
  return (
    <div className={`rounded-2xl border border-line bg-surface p-4 shadow-card ${className}`}>
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-xl bg-brand-100 text-brand-800">
          <Database className="size-5" strokeWidth={1.75} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-ink">{name}</span>
          <code className="block text-xs text-ink-muted">{node}</code>
        </span>
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
            online ? 'bg-success-50 text-success-700' : 'bg-info-50 text-info-700'
          }`}
        >
          <span className={`size-1.5 rounded-full ${online ? 'bg-success-600' : 'bg-info-600'}`} />
          {status}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
        {['DMI local', 'FHIR', 'Fédération'].map((x) => (
          <span key={x} className="rounded-lg bg-surface-muted px-2 py-1.5 text-center text-ink-soft">
            {x}
          </span>
        ))}
      </div>
    </div>
  )
}

function CellText({ title, body, icon: Icon }: { title: string; body: string; icon?: typeof Bot }) {
  return (
    <div>
      {Icon && <Icon aria-hidden className="mb-5 size-6 text-brand-700" strokeWidth={1.5} />}
      <h3 className="text-xl font-semibold text-ink">{title}</h3>
      <p className="mt-2 max-w-[40ch] text-[15px] leading-relaxed text-ink-soft">{body}</p>
    </div>
  )
}

/* ---------------- Trust: split, list on the right carries the content ---------------- */

export function Trust() {
  const s = copy.trust
  const icons = [Database, KeyRound, Fingerprint]
  return (
    <section id="confiance" aria-labelledby="trust-title" className="bg-brand-50 py-24 sm:py-32">
      <div className={`${wrap} grid gap-12 lg:grid-cols-12 lg:gap-8`}>
        <Reveal className="lg:col-span-5">
          <h2 id="trust-title" className={sectionTitle}>
            {s.title}
          </h2>
          <p className="mt-4 max-w-[34ch] text-lg leading-relaxed text-ink-soft" style={{ ['--i' as string]: 1 }}>
            {s.body}
          </p>
        </Reveal>
        <Reveal as="ul" className="grid gap-8 sm:grid-cols-3 lg:col-span-7 lg:grid-cols-1 lg:gap-10 lg:pl-12">
          {s.items.map((item, i) => {
            const Icon = icons[i] ?? ShieldCheck
            return (
              <li key={item.title} className="flex flex-col gap-4 lg:flex-row lg:gap-6" style={{ ['--i' as string]: i }}>
                <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-surface text-brand-700 shadow-card">
                  <Icon aria-hidden className="size-5" strokeWidth={1.75} />
                </span>
                <div>
                  <h3 className="text-lg font-semibold text-ink">{item.title}</h3>
                  <p className="mt-1 max-w-[46ch] text-[15px] leading-relaxed text-ink-soft">{item.body}</p>
                </div>
              </li>
            )
          })}
        </Reveal>
      </div>
    </section>
  )
}

/* ---------------- Hospitals: the onboarding path and the download button ---------------- */

export function Hospitals() {
  const c = copy.hospitals
  return (
    <section id="etablissements" aria-labelledby="hospitals-title" className="py-24 sm:py-32">
      <div className={wrap}>
        <Reveal className="relative overflow-hidden rounded-3xl bg-brand-950 px-6 py-16 sm:px-12 sm:py-20">
          <div
            aria-hidden
            className="pointer-events-none absolute top-0 left-1/2 h-[28rem] w-[46rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(closest-side,rgb(167_227_212/0.35),transparent)]"
          />
          <div className="relative text-center">
            <h2 id="hospitals-title" className="text-[clamp(2.6rem,6vw,5rem)] leading-[1.02] font-semibold tracking-[-0.045em] text-white">
              {c.title}
            </h2>
            <p className="mx-auto mt-4 max-w-[46ch] text-lg text-white/75">{c.body}</p>
          </div>
          <ol className="relative mx-auto mt-12 grid max-w-[60rem] gap-3 sm:grid-cols-3" style={{ ['--i' as string]: 1 }}>
            {c.steps.map((step, i) => (
              <li key={step.title} className="rounded-2xl border border-white/10 bg-white/5 p-5 text-left">
                <span className="tabular grid size-8 place-items-center rounded-full bg-brand-300 text-sm font-semibold text-on-mint">{i + 1}</span>
                <h3 className="mt-4 text-base font-semibold text-white">{step.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-white/65">{step.body}</p>
              </li>
            ))}
          </ol>
          <div className="relative mt-10 flex flex-wrap justify-center gap-3" style={{ ['--i' as string]: 2 }}>
            <LinkButton href={JOURNEY_START_HREF} size="xl" variant="mint" icon={Download}>
              {c.cta}
            </LinkButton>
            <a
              href={SIGN_IN_HREF}
              className="inline-flex h-14 items-center rounded-full px-6 text-base font-medium text-white/80 transition-colors hover:text-white"
            >
              {copy.nav.signIn}
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

export function Footer() {
  const f = copy.footer
  const cols = [
    {
      title: f.product,
      links: [
        { label: copy.nav.how, href: '#fonctionnement' },
        { label: copy.nav.ecosystem, href: '#ecosysteme' },
        { label: copy.nav.trust, href: '#confiance' },
      ],
    },
    {
      title: f.hospitals,
      links: [
        { label: "Parcours d'adhésion", href: JOURNEY_START_HREF },
        { label: copy.nav.signIn, href: SIGN_IN_HREF },
        { label: copy.nav.cta, href: JOURNEY_START_HREF },
      ],
    },
  ]
  return (
    <footer className="border-t border-line">
      <div className={`${wrap} grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-12`}>
        <div className="lg:col-span-8">
          <Logo />
          <p className="mt-3 max-w-[32ch] text-sm text-ink-soft">{f.tagline}</p>
        </div>
        {cols.map((col) => (
          <nav key={col.title} aria-label={col.title} className="lg:col-span-2">
            <h2 className="text-sm font-semibold text-ink">{col.title}</h2>
            <ul className="mt-3 space-y-2 text-sm text-ink-soft">
              {col.links.map((l) => (
                <li key={l.label}>
                  <a href={l.href} className="rounded transition-colors hover:text-ink">
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className={`${wrap} border-t border-line py-6 text-xs text-ink-muted`}>{f.rights}</div>
    </footer>
  )
}
