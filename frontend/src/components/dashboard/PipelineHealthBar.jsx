import { useNavigate } from 'react-router-dom'
import { usePipelineStats } from '@/hooks/usePipelineStats'
import { CLIENT_STAGES, CLIENT_STAGE_LABELS, INVESTOR_STAGES, INVESTOR_STAGE_LABELS, STAGE_COLORS } from '@/lib/constants'

function StageBar({ label, stages, stageCounts, link, stageLabels }) {
  const navigate = useNavigate()
  const total = stages.reduce((s, k) => s + (stageCounts[k] ?? 0), 0)
  if (total === 0) return (
    <div className="mb-5">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-gray-400 uppercase tracking-widest">{label}</span>
        <span className="font-data text-gray-600">0 records</span>
      </div>
      <div className="h-2 bg-muted/30 rounded-full" />
    </div>
  )

  return (
    <div className="mb-5">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-gray-400 uppercase tracking-widest">{label}</span>
        <span className="font-data text-gray-500">{total} total</span>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
        {stages.map((stage) => {
          const count = stageCounts[stage] ?? 0
          if (!count) return null
          const pct = (count / total) * 100
          return (
            <div
              key={stage}
              title={`${stageLabels[stage]}: ${count}`}
              className="cursor-pointer hover:opacity-80 transition-opacity rounded-sm"
              style={{ width: `${pct}%`, backgroundColor: STAGE_COLORS[stage] ?? '#374151' }}
              onClick={() => navigate(link)}
            />
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        {stages.filter(s => (stageCounts[s] ?? 0) > 0).map(stage => (
          <span key={stage} className="text-xs text-gray-500 flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm inline-block" style={{ backgroundColor: STAGE_COLORS[stage] }} />
            {stageLabels[stage]} <span className="font-data">{stageCounts[stage]}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

export function PipelineHealthBar() {
  const { clientStageCounts, investorStageCounts } = usePipelineStats()
  return (
    <div>
      <StageBar
        label="Client Pipeline"
        stages={CLIENT_STAGES}
        stageLabels={CLIENT_STAGE_LABELS}
        stageCounts={clientStageCounts}
        link="/clients"
      />
      <StageBar
        label="Investor Pipeline"
        stages={INVESTOR_STAGES}
        stageLabels={INVESTOR_STAGE_LABELS}
        stageCounts={investorStageCounts}
        link="/investors"
      />
    </div>
  )
}
