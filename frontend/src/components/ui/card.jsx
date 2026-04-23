import { cn } from '@/lib/utils'

export function Card({ className, ...props }) {
  return <div className={cn('rounded-lg border border-muted/50 bg-charcoal', className)} {...props} />
}
export function CardHeader({ className, ...props }) {
  return <div className={cn('flex flex-col space-y-1 p-5', className)} {...props} />
}
export function CardTitle({ className, ...props }) {
  return <h3 className={cn('text-xs font-medium text-gray-400 uppercase tracking-widest', className)} {...props} />
}
export function CardContent({ className, ...props }) {
  return <div className={cn('p-5 pt-0', className)} {...props} />
}
