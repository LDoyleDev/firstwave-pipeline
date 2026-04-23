import { useState } from 'react'
import { KanbanBoard } from '@/components/pipeline/KanbanBoard'
import { LeadDetailSheet } from '@/components/pipeline/LeadDetailSheet'
import { useAllLeads, useUpdateLead } from '@/hooks/useLeads'
import { Skeleton } from '@/components/ui/skeleton'

export default function Clients() {
  const { data: leads = [], isLoading } = useAllLeads()
  const updateLead = useUpdateLead()
  const [selected, setSelected] = useState(null)

  if (isLoading) return (
    <div className="flex gap-3">
      {[...Array(6)].map((_,i) => <Skeleton key={i} className="h-96 w-[200px] shrink-0" />)}
    </div>
  )

  return (
    <>
      <div className="mb-4">
        <span className="text-xs text-gray-500">
          <span className="font-data text-white">{leads.length}</span> leads across all stages
        </span>
      </div>
      <KanbanBoard
        leads={leads}
        onStageChange={(id, newStage) => updateLead.mutate({ id, data: { pipeline_stage: newStage } })}
        onCardClick={setSelected}
      />
      <LeadDetailSheet lead={selected} onClose={() => setSelected(null)} />
    </>
  )
}
