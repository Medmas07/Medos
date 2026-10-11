import { GatherChapter, Hero, ShareChapter } from './Chapters'
import { copy } from './copy'
import { Features, Footer, Hospitals, Trust } from './Sections'
import { SiteNav } from './SiteNav'
import { Story } from './Story'

/** MedOS landing page: scroll-driven 3D story, ecosystem, trust, and the hospital download path. */
export function Landing() {
  return (
    <>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-xl focus:bg-surface focus:px-4 focus:py-2 focus:shadow-pop"
      >
        {copy.nav.skip}
      </a>
      <SiteNav />
      <main id="main">
        <Story>
          <Hero />
          <GatherChapter />
          <ShareChapter />
        </Story>
        <Features />
        <Trust />
        <Hospitals />
      </main>
      <Footer />
    </>
  )
}
