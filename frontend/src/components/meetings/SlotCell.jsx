import { OutcomeBadge } from './OutcomeBadge'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export function SlotCell({ slot, time, meeting, isPast }) {
  if (!meeting) return (
    <div className={cn(
      'h-20 rounded border flex flex-col items-center justify-center text-xs transition-colors',
      isPast ? 'border-muted/20 opacity-40' : 'border-green-500/20 hover:border-green-500/40 cursor-pointer',
    )}>
      <span className="font-data text-gray-500">{time}</span>
      {!isPast && <span className="text-green-400/70 mt-1">AVAILABLE</span>}
    </div>
  )

  const name = meeting.leads
    ? `${meeting.leads.first_name} ${meeting.leads.last_name}`
    : meeting.investor_targets?.firm_name ?? '—'

  return (
    <div className={cn(
      'h-20 rounded border p-2 cursor-pointer hover:border-accent/60 transition-colors',
      'border-accent/30 bg-accent/5',
    )}>
      <div className="font-data text-xs text-gray-400 mb-1">{time}</div>
      <div className="text-xs font-medium text-white truncate">{name}</div>
      <div className="flex items-center gap-1 mt-1">
        <Badge variant={meeting.track === 'client' ? 'client' : 'investor'} className="text-[10px]">
          {meeting.track?.slice(0,3).toUpperCase()}
        </Badge>
        <OutcomeBadge outcome={meeting.outcome} />
      </div>
    </div>
  )
}
