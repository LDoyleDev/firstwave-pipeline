import { ResponsiveContainer, FunnelChart, Funnel, Tooltip, LabelList } from 'recharts'
import { CLIENT_STAGES, CLIENT_STAGE_LABELS, STAGE_COLORS } from '@/lib/constants'
import { useAllLeads } from '@/hooks/useLeads'

export function ConversionFunnel() {
  const { data: leads = [] } = useAllLeads()
  const displayStages = ['discovered','enriched','review_queue','approved','contacted','replied','meeting_booked','met','closed_won']
  const data = displayStages.map(stage => ({
    name: CLIENT_STAGE_LABELS[stage],
    value: leads.filter(l => l.pipeline_stage === stage).length,
    fill: STAGE_COLORS[stage],
  })).filter(d => d.value > 0)

  if (!data.length) return (
    <div className="h-48 flex items-center justify-center text-gray-600 text-sm">No client leads yet</div>
  )

  return (
    <ResponsiveContainer width="100%" height={220}>
      <FunnelChart>
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1d2e', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }}
          labelStyle={{ color: '#9ca3af' }}
          itemStyle={{ color: '#e5e7eb' }}
        />
        <Funnel dataKey="value" data={data} isAnimationActive={false}>
          <LabelList position="right" fill="#9ca3af" fontSize={11} dataKey="name" />
          <LabelList position="insideRight" fill="#fff" fontSize={11} fontFamily="monospace" dataKey="value" />
        </Funnel>
      </FunnelChart>
    </ResponsiveContainer>
  )
}
