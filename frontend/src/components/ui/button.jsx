import { cn } from '@/lib/utils'

const variants = {
  default: 'bg-accent hover:bg-accent-hover text-white',
  outline: 'border border-muted text-gray-300 hover:bg-muted/30 hover:text-white',
  ghost:   'text-gray-400 hover:bg-muted/30 hover:text-white',
  danger:  'bg-red-600/80 hover:bg-red-600 text-white',
  success: 'bg-green-600/80 hover:bg-green-600 text-white',
}
const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
  icon: 'p-2',
}

export function Button({ variant = 'default', size = 'md', className, ...props }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant], sizes[size], className,
      )}
      {...props}
    />
  )
}
