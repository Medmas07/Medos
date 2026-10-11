import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { copy } from './copy'
import { SceneFallback } from './SceneFallback'
import { finishIntro, story } from './story'

// Three.js only downloads when the device can actually run the scene.
const Scene = lazy(() => import('./Scene'))

type Mode = 'unknown' | 'webgl' | 'fallback'

function hasWebGL() {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
}

/** Phones and narrow tablets get the static scene. */
function canRender3D() {
  return window.matchMedia('(min-width: 768px)').matches && hasWebGL()
}

export function Story({ children }: { children: ReactNode }) {
  const sectionRef = useRef<HTMLElement>(null)
  const [mode, setMode] = useState<Mode>('unknown')
  const [reduced, setReduced] = useState(false)
  const [active, setActive] = useState(true)

  // capability + motion preference
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(mq.matches)
    update()
    mq.addEventListener('change', update)
    const next = canRender3D() ? 'webgl' : 'fallback'
    setMode(next)
    if (next === 'fallback') finishIntro()
    // never hold the page hostage: reveal the hero even if the scene stalls
    const safety = window.setTimeout(finishIntro, 2600)
    return () => {
      mq.removeEventListener('change', update)
      window.clearTimeout(safety)
    }
  }, [])

  // smooth scroll + progress, only when motion is welcome
  useEffect(() => {
    if (reduced || !sectionRef.current) return
    let cleanup = () => {}
    let cancelled = false
    void (async () => {
      const [{ default: Lenis }, { gsap }, { ScrollTrigger }] = await Promise.all([
        import('lenis'),
        import('gsap'),
        import('gsap/ScrollTrigger'),
      ])
      if (cancelled || !sectionRef.current) return
      gsap.registerPlugin(ScrollTrigger)
      const lenis = new Lenis({ lerp: 0.1, anchors: true })
      const raf = (time: number) => lenis.raf(time * 1000)
      lenis.on('scroll', ScrollTrigger.update)
      gsap.ticker.add(raf)
      gsap.ticker.lagSmoothing(0)
      const trigger = ScrollTrigger.create({
        trigger: sectionRef.current,
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => {
          story.progress = self.progress
          if (self.progress > 0.01) finishIntro()
        },
      })
      cleanup = () => {
        trigger.kill()
        gsap.ticker.remove(raf)
        lenis.destroy()
      }
    })()
    return () => {
      cancelled = true
      cleanup()
    }
  }, [reduced])

  // stop rendering once the story has scrolled away
  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => setActive(!!entry?.isIntersecting), { rootMargin: '10% 0px' })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <section ref={sectionRef} id="story" aria-label={copy.hero.title} className="relative">
      {/* Stage: an absolute track the height of the story, with a sticky viewport inside,
          so it pins for exactly the story and never overruns the next section */}
      <div className="absolute inset-0">
        <div className="sticky top-0 h-[100svh] overflow-hidden" data-testid="story-stage">
          <div aria-hidden className="atmosphere absolute inset-0" />
          {mode === 'webgl' ? (
            <div className="absolute inset-0" data-camera={reduced ? 'static' : 'scroll'}>
              <Suspense fallback={null}>
                <Scene reduced={reduced} active={active} />
              </Suspense>
            </div>
          ) : mode === 'fallback' ? (
            <SceneFallback />
          ) : null}
          {/* keeps the headline column legible over the scene */}
          <div aria-hidden className="pointer-events-none absolute inset-y-0 left-0 w-full bg-gradient-to-r from-paper/85 via-paper/40 to-transparent md:w-[62%]" />
          <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-paper to-transparent" />
          <IntroLabel />
        </div>
      </div>
      <div className="relative">{children}</div>
    </section>
  )
}

function IntroLabel() {
  return (
    <div aria-hidden className="intro-label pointer-events-none absolute inset-x-0 bottom-[22svh] flex flex-col items-center gap-3">
      <span className="text-sm font-medium tracking-wide text-ink-soft">{copy.loader}</span>
      <span className="h-px w-32 overflow-hidden rounded-full bg-line">
        <span className="intro-bar block h-full w-full origin-left bg-brand-600" />
      </span>
    </div>
  )
}
