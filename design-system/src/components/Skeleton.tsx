import { cx } from '../cx'

export interface SkeletonProps {
  /** Size and shape, for example `h-4 w-32` or `h-28 rounded-2xl`. */
  className?: string
}

/** Decorative shimmering placeholder. Pair it with a status label (see `LoadingState`). */
export function Skeleton({ className }: SkeletonProps) {
  return <div aria-hidden="true" className={cx('hc-skeleton rounded-xl', className)} />
}
