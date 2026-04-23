import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts'
import { TIER_LABELS } from '@/lib/constants'
import { useAllInvestors } from '@/hooks/useInvestors'

export function InvestorTierCoverage() {
  const { data: investors = [] } = useAllInvestors()

  const data = [1,2,3,4,5,6].map(tier => {
    const group = investors.filter(i => i.tier === tier)
    return {
      tier: `T${tier}`,
      notStarted: group.filter(i => ['identified','research_needed'].includes(i.pipeline_stage)).length,
      inContact:  group.filter(i => ['ready_to_contact','contacted','replied'].includes(i.pipeline_stage)).length,
      advanced:   group.filter(i => ['meeting_booked','met','term_sheet'].includes(i.pipeline_stage)).length,
      closed:     group.filter(i => ['closed','pass'].includes(i.pipeline_stage)).length,
    }
  })

  const labelStyle = { fill: '#9ca3af', fontSize: 11 }
  const tooltipStyle = { backgroundColor: '#1a1d2e', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
        <XAxis dataKey="tier" tick={labelStyle} axisLine={false} tickLine={false} />
        <YAxis tick={labelStyle} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: '#9ca3af' }} />
        <Bar dataKey="notStarted" name="Not Started" stackId="a" fill="#374151" />
        <Bar dataKey="inContact"  name="In Contact"  stackId="a" fill="#2563eb" />
        <Bar dataKey="advanced"   name="Advanced"    stackId="a" fill="#f59e0b" />
        <Bar dataKey="closed"     name="Closed"      stackId="a" fill="#22c55e" radius={[3,3,0,0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
