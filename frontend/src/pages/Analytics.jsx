import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { ConversionFunnel }     from '@/components/analytics/ConversionFunnel'
import { ReplyRateChart }       from '@/components/analytics/ReplyRateChart'
import { InvestorTierCoverage } from '@/components/analytics/InvestorTierCoverage'
import { MeetingOutcomesChart } from '@/components/analytics/MeetingOutcomesChart'
import { usePipelineStats }     from '@/hooks/usePipelineStats'

export default function Analytics() {
  const stats = usePipelineStats()
  const replyRate = stats.totalLeads > 0
    ? Math.round((stats.repliesThisWeek / Math.max(stats.activeInSequence, 1)) * 100)
    : 0
  const investorCoverage = Math.round(
    (stats.totalInvestors > 0
      ? stats.investorStageCounts
        ? Object.entries(stats.investorStageCounts).filter(([s]) => !['identified','research_needed'].includes(s)).reduce((a,[,v]) => a+v, 0)
        : 0
      : 0) / Math.max(stats.totalInvestors, 1) * 100
  )

  const kpis = [
    { label: 'Total Leads',         value: stats.totalLeads },
    { label: 'Reply Rate',          value: `${replyRate}%` },
    { label: 'Investor Coverage',   value: `${investorCoverage}%` },
    { label: 'Investor Targets',    value: stats.totalInvestors },
  ]

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="grid grid-cols-4 gap-4">
        {kpis.map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="pt-5">
              <div className="text-xs text-gray-500 uppercase tracking-widest mb-2">{label}</div>
              <div className="font-data text-3xl font-medium text-white">{value ?? '—'}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle>Client Conversion Funnel</CardTitle></CardHeader>
        <CardContent><ConversionFunnel /></CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Weekly Outreach vs Replies</CardTitle></CardHeader>
          <CardContent><ReplyRateChart /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Investor Coverage by Tier</CardTitle></CardHeader>
          <CardContent><InvestorTierCoverage /></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Meeting Outcomes</CardTitle></CardHeader>
        <CardContent><MeetingOutcomesChart /></CardContent>
      </Card>
    </div>
  )
}
