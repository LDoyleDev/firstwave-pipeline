import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }) {
  return (
    <div className={cn('animate-pulse rounded bg-muted/40', className)} {...props} />
  )
}
