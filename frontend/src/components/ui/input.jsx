import { cn } from '@/lib/utils'

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(
        'w-full rounded border border-muted bg-navy px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-accent focus:outline-none transition-colors',
        className,
      )}
      {...props}
    />
  )
}
