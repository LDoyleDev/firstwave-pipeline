import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { MeetingSlotsPanel }  from '@/components/dashboard/MeetingSlotsPanel'
import { KpiCard }            from '@/components/dashboard/KpiCard'
import { PipelineHealthBar }  from '@/components/dashboard/PipelineHealthBar'
import { ActivityFeed }       from '@/components/dashboard/ActivityFeed'
import { ActionPanel }        from '@/components/dashboard/ActionPanel'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { usePipelineStats } from '@/hooks/usePipelineStats'
import { apiFetch } from '@/api/client'

function VelocityCard({ stats }) {
  const { data: brief } = useQuery({
    queryKey: ['morning-brief-stats'],
    queryFn: () => apiFetch('/status/morning-brief'),
    refetchInterval: 60000,
    staleTime: 30000,
  })

  const meetingsThisWeek = brief?.stats?.meetings_this_week ?? stats.meetingsThisWeek
  const target = brief?.stats?.meeting_target_weekly ?? 8
  const pct = Math.round((meetingsThisWeek / target) * 100)
  const onTrack = meetingsThisWeek >= Math.round(target * 0.7)

  const replyRate = brief?.stats?.reply_rate_30d
  const stale = brief?.stats?.stale_leads ?? 0

  return (
    <Card>
      <CardHeader><CardTitle>Velocity</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Meetings this week</span>
            <span className={onTrack ? 'text-green-400' : 'text-amber-400'}>
              {meetingsThisWeek} / {target}
            </span>
          </div>
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${onTrack ? 'bg-green-500' : 'bg-amber-500'}`}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
        </div>

        {replyRate != null && (
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Reply rate (30d)</span>
            <span className="text-white font-mono">{replyRate}%</span>
          </div>
        )}

        {stale > 0 && (
          <div className="text-xs text-amber-400">
            {stale} lead{stale > 1 ? 's' : ''} stuck &gt; 30 days — consider re-engagement
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const stats = usePipelineStats()

  return (
    <div className="space-y-6 max-w-6xl">
      <MeetingSlotsPanel />

      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Review Queue"
          value={stats.reviewQueue.total}
          alert={stats.reviewQueue.total > 5}
          onClick={() => navigate('/review')}
        />
        <KpiCard
          label="Active in Sequence"
          value={stats.activeInSequence}
          onClick={() => navigate('/clients')}
        />
        <KpiCard
          label="Replies This Week"
          value={stats.repliesThisWeek}
          trend={stats.repliesThisWeek > 0 ? 1 : 0}
          trendLabel="this week"
        />
        <KpiCard
          label="Meetings This Week"
          value={stats.meetingsThisWeek}
          onClick={() => navigate('/meetings')}
        />
      </div>

      <ActionPanel />

      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-3">
          <Card>
            <CardHeader><CardTitle>Pipeline Health</CardTitle></CardHeader>
            <CardContent><PipelineHealthBar /></CardContent>
          </Card>
        </div>
        <div className="col-span-2 space-y-4">
          <VelocityCard stats={stats} />
          <Card>
            <CardHeader><CardTitle>Recent Activity</CardTitle></CardHeader>
            <CardContent><ActivityFeed /></CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
