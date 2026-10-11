/**
 * Mutable scroll/intro state shared between the DOM scroll driver (GSAP ScrollTrigger)
 * and the WebGL scene. Plain object, read inside useFrame: no React re-renders per frame.
 */
export const story = {
  /** 0..1 across the pinned story section */
  progress: 0,
  /** intro loader: "pending" until the particle wordmark has played */
  intro: 'pending' as 'pending' | 'playing' | 'done',
}

/** Chapter windows on the story progress (chapter heights: 100 / 140 / 160 svh). */
export const BEATS = {
  gather: [0.1, 0.42] as const,
  threads: [0.42, 0.62] as const,
  focus: [0.64, 0.84] as const,
}

export function finishIntro() {
  if (story.intro === 'done') return
  story.intro = 'done'
  document.documentElement.dataset.intro = 'done'
}
