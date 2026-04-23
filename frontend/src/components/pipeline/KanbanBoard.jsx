import { useState } from 'react'
import { DndContext, closestCorners, DragOverlay, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { arrayMove } from '@dnd-kit/sortable'
import { KanbanColumn } from './KanbanColumn'
import { LeadCard } from './LeadCard'
import { CLIENT_STAGES } from '@/lib/constants'

export function KanbanBoard({ leads, onStageChange, onCardClick }) {
  const [activeId, setActiveId] = useState(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  const grouped = CLIENT_STAGES.reduce((acc, stage) => {
    acc[stage] = leads.filter(l => l.pipeline_stage === stage)
    return acc
  }, {})

  const activeLead = activeId ? leads.find(l => l.id === activeId) : null

  function handleDragEnd({ active, over }) {
    setActiveId(null)
    if (!over) return
    const oldStage = active.data.current?.sortable?.containerId ?? leads.find(l => l.id === active.id)?.pipeline_stage
    const newStage = over.id in grouped ? over.id : leads.find(l => l.id === over.id)?.pipeline_stage
    if (oldStage && newStage && oldStage !== newStage) {
      onStageChange?.(active.id, newStage)
    }
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={({ active }) => setActiveId(active.id)} onDragEnd={handleDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-4" style={{ minHeight: '60vh' }}>
        {CLIENT_STAGES.map(stage => (
          <KanbanColumn
            key={stage}
            stage={stage}
            leads={grouped[stage] ?? []}
            onCardClick={onCardClick}
          />
        ))}
      </div>
      <DragOverlay>
        {activeLead && <LeadCard lead={activeLead} />}
      </DragOverlay>
    </DndContext>
  )
}
