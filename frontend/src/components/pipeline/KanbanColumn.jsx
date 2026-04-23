import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { LeadCard } from './LeadCard'
import { cn } from '@/lib/utils'
import { STAGE_COLORS, CLIENT_STAGE_LABELS } from '@/lib/constants'

export function KanbanColumn({ stage, leads, onCardClick }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage })

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex flex-col min-w-[200px] w-[200px] rounded-lg border bg-charcoal/50 transition-colors',
        isOver ? 'border-accent/60 bg-accent/5' : 'border-muted/30',
      )}
    >
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-muted/30">
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: STAGE_COLORS[stage] ?? '#374151' }}
        />
        <span className="text-xs font-medium text-gray-300 flex-1 truncate">
          {CLIENT_STAGE_LABELS[stage] ?? stage}
        </span>
        <span className="font-data text-xs text-gray-600">{leads.length}</span>
      </div>
      <div className="flex-1 p-2 space-y-2 min-h-[120px] overflow-y-auto">
        <SortableContext items={leads.map(l => l.id)} strategy={verticalListSortingStrategy}>
          {leads.map(lead => (
            <LeadCard key={lead.id} lead={lead} onClick={onCardClick} />
          ))}
        </SortableContext>
      </div>
    </div>
  )
}
