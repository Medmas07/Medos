import { useEffect, useRef, type ComponentProps } from 'react'

/** Children fade and rise in sequence when the block enters the viewport. CSS does the motion. */
export function Reveal({ className, as: Tag = 'div', ...rest }: ComponentProps<'div'> & { as?: 'div' | 'header' | 'ul' }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          el.dataset.inview = 'true'
          io.disconnect()
        }
      },
      { rootMargin: '0px 0px -12% 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])
  const Comp = Tag as 'div'
  return <Comp ref={ref} className={['reveal', className].filter(Boolean).join(' ')} {...rest} />
}
