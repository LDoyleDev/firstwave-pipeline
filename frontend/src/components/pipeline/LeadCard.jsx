import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { cn } from '@/lib/utils'
import { WARMTH_COLORS } from '@/lib/constants'
import { differenceInDays, parseISO } from 'date-fns'

export function LeadCard({ lead, onClick }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: lead.id })

  const style = { transform: CSS.Transform.toString(transform), transition }
  const daysInStage = differenceInDays(new Date(), parseISO(lead.updated_at))

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => onClick?.(lead)}
      className={cn(
        'bg-navy border border-muted/40 rounded p-3 cursor-pointer hover:border-accent/40 transition-colors select-none',
        isDragging && 'opacity-50 shadow-xl border-accent',
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <div className="text-xs font-medium text-white truncate">{lead.first_name} {lead.last_name}</div>
          <div className="text-xs text-gray-500 truncate">{lead.title}</div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: WARMTH_COLORS[lead.warmth] ?? WARMTH_COLORS.cold }}
            title={lead.warmth}
          />
          {lead.lead_score > 0 && (
            <span className="font-data text-xs text-gray-400">{lead.lead_score}</span>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-600 truncate">{lead.source ?? 'manual'}</span>
        <span className="font-data text-xs text-gray-600">{daysInStage}d</span>
      </div>
    </div>
  )
}
