import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { ConversionFunnel }     from '@/components/analytics/ConversionFunnel'
import { ReplyRateChart }       from '@/components/analytics/ReplyRateChart'
import { InvestorTierCoverage } from '@/components/analytics/InvestorTierCoverage'
import { MeetingOutcomesChart } from '@/components/analytics/MeetingOutcomesChart'
import { apiFetch } from '@/api/client'

function StatRow({ label, value, highlight }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-gray-800 last:border-0">
      <span className="text-xs text-gray-400">{label}</span>
      <span className={`text-sm font-mono ${highlight ? 'text-green-400' : 'text-white'}`}>{value ?? '—'}</span>
    </div>
  )
}

function FunnelRates({ rates }) {
  if (!rates) return null
  return (
    <div className="space-y-1">
      <StatRow label="Enrichment rate"  value={`${Math.round((rates.enrichment_rate  || 0) * 100)}%`} />
      <StatRow label="Contact → Reply"  value={`${Math.round((rates.contact_to_reply || 0) * 100)}%`} highlight={(rates.contact_to_reply || 0) >= 0.05} />
      <StatRow label="Reply → Meeting"  value={`${Math.round((rates.reply_to_meeting || 0) * 100)}%`} highlight={(rates.reply_to_meeting || 0) >= 0.2} />
      <StatRow label="Meeting → Close"  value={`${Math.round((rates.meeting_to_close || 0) * 100)}%`} />
    </div>
  )
}

function TopTable({ title, data, maxRows = 5 }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div>
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">{title}</div>
        <div className="text-xs text-gray-600">No data yet</div>
      </div>
    )
  }
  const sorted = Object.entries(data)
    .sort(([, a], [, b]) => (b.reply_rate ?? b.rate ?? 0) - (a.reply_rate ?? a.rate ?? 0))
    .slice(0, maxRows)

  return (
    <div>
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">{title}</div>
      {sorted.map(([name, vals]) => {
        const rate = vals.reply_rate ?? vals.rate ?? 0
        const pct  = Math.round(rate * 100)
        const sent = vals.contacted ?? vals.sent ?? 0
        return (
          <div key={name} className="flex items-center gap-2 py-1">
            <span className="text-xs text-gray-300 w-36 truncate">{name}</span>
            <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.min(pct * 5, 100)}%` }} />
            </div>
            <span className="text-xs font-mono text-white w-10 text-right">{pct}%</span>
            <span className="text-xs text-gray-600 w-12 text-right">n={sent}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function Analytics() {
  const { data: conv, isLoading } = useQuery({
    queryKey: ['conversion-30d'],
    queryFn: () => apiFetch('/analytics/conversion?days=30&track=client'),
    refetchInterval: 120000,
    staleTime: 60000,
  })

  const funnel   = conv?.funnel
  const rates    = conv?.rates
  const velocity = conv?.velocity

  const totalLeads = funnel
    ? funnel.discovered + funnel.enriched + funnel.contacted + funnel.replied + funnel.meeting_booked
    : null

  const kpis = [
    { label: 'Total Leads',        value: totalLeads ?? '—' },
    { label: 'Reply Rate (30d)',    value: rates   ? `${Math.round((rates.contact_to_reply  || 0) * 100)}%`  : '—' },
    { label: 'Reply → Meeting',    value: rates   ? `${Math.round((rates.reply_to_meeting  || 0) * 100)}%`  : '—' },
    { label: 'Avg Days to Reply',  value: velocity?.avg_days_to_reply != null ? `${velocity.avg_days_to_reply}d` : '—' },
  ]

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="grid grid-cols-4 gap-4">
        {kpis.map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="pt-5">
              <div className="text-xs text-gray-500 uppercase tracking-widest mb-2">{label}</div>
              <div className="font-data text-3xl font-medium text-white">{value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle>Client Conversion Funnel</CardTitle></CardHeader>
          <CardContent><ConversionFunnel /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Conversion Rates</CardTitle></CardHeader>
          <CardContent>
            {isLoading
              ? <div className="text-xs text-gray-500">Loading...</div>
              : <FunnelRates rates={rates} />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Velocity</CardTitle></CardHeader>
          <CardContent>
            {velocity && (
              <div className="space-y-1">
                <StatRow
                  label="Meetings this week"
                  value={`${velocity.meetings_this_week} / ${velocity.meeting_target_weekly}`}
                  highlight={velocity.on_track}
                />
                <StatRow
                  label="Avg days to reply"
                  value={velocity.avg_days_to_reply != null ? `${velocity.avg_days_to_reply}d` : '—'}
                  highlight={velocity.avg_days_to_reply != null && velocity.avg_days_to_reply <= 5}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

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

      {conv && (
        <Card>
          <CardHeader><CardTitle>What's Working</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-6">
              <TopTable title="By market"          data={conv.by_market} />
              <TopTable title="By title"           data={conv.by_title} />
              <TopTable title="By subject pattern" data={
                Object.fromEntries(
                  Object.entries(conv.by_subject_pattern || {}).map(([k, v]) => [k, { ...v, reply_rate: v.rate }])
                )
              } />
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Meeting Outcomes</CardTitle></CardHeader>
        <CardContent><MeetingOutcomesChart /></CardContent>
      </Card>
    </div>
  )
}
