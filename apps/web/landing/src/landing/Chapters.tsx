import { ArrowDown, Download, FileClock, Network, Scale, ServerCog } from 'lucide-react'
import { copy } from './copy'
import { LinkButton } from './LinkButton'
import { Reveal } from './Reveal'
import { JOURNEY_START_HREF } from './links'

const wrap = 'mx-auto w-full max-w-[1320px] px-4 sm:px-8 lg:px-12'
const chapterTitle = 'text-[clamp(2.5rem,5.4vw,4.75rem)] leading-[1.02] font-semibold tracking-[-0.045em] text-ink'

export function Hero() {
  const h = copy.hero
  return (
    <div className="relative flex min-h-[100svh] items-center pt-24 pb-16">
      <div className={wrap}>
        <div className="max-w-[40rem]">
          <p className="intro-hide inline-flex items-center gap-2 rounded-full glass px-3 py-1 text-[13px] font-medium text-ink-soft" style={{ ['--i' as string]: 0 }}>
            <span className="size-1.5 rounded-full bg-brand-500" aria-hidden />
            Écosystème de santé fédéré
          </p>
          <h1
            className="intro-hide mt-5 pb-1 text-[clamp(3.25rem,8.2vw,7.25rem)] leading-[0.96] font-semibold tracking-[-0.05em] text-ink"
            style={{ ['--i' as string]: 1 }}
          >
            {h.title}
          </h1>
          <p className="intro-hide mt-6 max-w-[38ch] text-lg leading-relaxed text-ink-soft sm:text-xl" style={{ ['--i' as string]: 2 }}>
            {h.body}
          </p>
          <div className="intro-hide mt-9 flex flex-wrap gap-3" style={{ ['--i' as string]: 3 }}>
            <LinkButton href={JOURNEY_START_HREF} size="lg" icon={Download}>
              {h.primary}
            </LinkButton>
            <LinkButton href="#fonctionnement" size="lg" variant="glass" iconRight={ArrowDown}>
              {h.secondary}
            </LinkButton>
          </div>
        </div>
      </div>
    </div>
  )
}

export function GatherChapter() {
  const c = copy.gather
  return (
    <div id="fonctionnement" className="relative flex min-h-[140svh] items-center py-24">
      <div className={wrap}>
        <Reveal className="max-w-[32rem]">
          <h2 className={chapterTitle}>{c.title}</h2>
          <p className="mt-5 text-lg leading-relaxed text-ink-soft" style={{ ['--i' as string]: 1 }}>
            {c.body}
          </p>
          <ul className="mt-8 flex flex-wrap gap-2" style={{ ['--i' as string]: 2 }}>
            {c.chips.map((chip) => (
              <li key={chip} className="glass inline-flex h-9 items-center gap-2 rounded-full px-3.5 text-sm font-medium text-ink">
                <ServerCog aria-hidden className="size-4 text-brand-700" strokeWidth={1.75} />
                {chip}
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </div>
  )
}

export function ShareChapter() {
  const c = copy.share
  const icons = [Scale, FileClock, Network]
  return (
    <div className="relative flex min-h-[160svh] items-center py-24">
      <div className={wrap}>
        <Reveal className="max-w-[32rem]">
          <h2 className={chapterTitle}>{c.title}</h2>
          <p className="mt-5 text-lg leading-relaxed text-ink-soft" style={{ ['--i' as string]: 1 }}>
            {c.body}
          </p>
          <ul className="mt-8 space-y-2" style={{ ['--i' as string]: 2 }}>
            {c.chips.map((chip, i) => {
              const Icon = icons[i] ?? Network
              return (
                <li key={chip} className="glass flex h-12 w-fit items-center gap-3 rounded-2xl pr-4 pl-2 text-[15px] font-medium text-ink">
                  <span className="grid size-8 place-items-center rounded-xl bg-brand-100 text-brand-800">
                    <Icon aria-hidden className="size-4" strokeWidth={1.75} />
                  </span>
                  {chip}
                </li>
              )
            })}
          </ul>
        </Reveal>
      </div>
    </div>
  )
}
