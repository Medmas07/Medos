import { copy } from './copy'

/**
 * Static stand-in for the WebGL scene (phones, no WebGL). Pure CSS: a mint
 * atmosphere with a few soft record silhouettes settling into one node.
 */
export function SceneFallback() {
  return (
    <div role="img" aria-label={copy.fallback} className="absolute inset-0">
      <div className="absolute top-[18%] right-[-18%] h-[62vmax] w-[62vmax] rounded-full bg-[radial-gradient(closest-side,var(--color-brand-300),transparent)] opacity-60 md:right-[-6%]" />
      <div className="absolute right-[6%] bottom-[8%] md:right-[16%]">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="absolute h-44 w-34 rounded-2xl border border-white/80 bg-white/55 shadow-lift backdrop-blur-sm md:h-60 md:w-46"
            style={{
              transform: `translate(${-i * 26}px, ${-i * 30}px) rotate(${(i - 2) * 5}deg)`,
              opacity: 1 - i * 0.14,
            }}
          >
            <div className="m-4 h-2 w-1/2 rounded-full bg-brand-950/45" />
            <div className="mx-4 mt-3 space-y-2">
              <div className="h-1.5 w-4/5 rounded-full bg-brand-950/15" />
              <div className="h-1.5 w-3/5 rounded-full bg-brand-950/15" />
              <div className="h-1.5 w-2/3 rounded-full bg-brand-950/15" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
