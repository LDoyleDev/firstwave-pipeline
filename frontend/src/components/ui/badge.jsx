import { cn } from '@/lib/utils'

const variants = {
  default:  'bg-accent/20 text-accent border border-accent/30',
  success:  'bg-green-500/20 text-green-400 border border-green-500/30',
  warning:  'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  danger:   'bg-red-500/20 text-red-400 border border-red-500/30',
  muted:    'bg-muted/50 text-gray-400 border border-muted',
  hot:      'bg-red-500/20 text-red-400 border border-red-500/30',
  warm:     'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  cold:     'bg-slate-500/20 text-slate-400 border border-slate-500/30',
  client:   'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  investor: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
}

export function Badge({ variant = 'default', className, ...props }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium font-data',
        variants[variant] ?? variants.default,
        className,
      )}
      {...props}
    />
  )
}
