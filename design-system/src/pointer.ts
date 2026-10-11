import type { PointerEvent } from 'react'

/** Stores the pointer position on the element as --hc-x / --hc-y for the `hc-spot` glow. */
export function trackPointer(event: PointerEvent<HTMLElement>) {
  const target = event.currentTarget
  const rect = target.getBoundingClientRect()
  target.style.setProperty('--hc-x', `${event.clientX - rect.left}px`)
  target.style.setProperty('--hc-y', `${event.clientY - rect.top}px`)
}
