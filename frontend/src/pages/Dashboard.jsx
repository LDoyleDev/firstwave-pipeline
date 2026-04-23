import { useNavigate } from 'react-router-dom'
import { MeetingSlotsPanel }  from '@/components/dashboard/MeetingSlotsPanel'
import { KpiCard }            from '@/components/dashboard/KpiCard'
import { PipelineHealthBar }  from '@/components/dashboard/PipelineHealthBar'
import { ActivityFeed }       from '@/components/dashboard/ActivityFeed'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { usePipelineStats } from '@/hooks/usePipelineStats'

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

      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-3">
          <Card>
            <CardHeader><CardTitle>Pipeline Health</CardTitle></CardHeader>
            <CardContent><PipelineHealthBar /></CardContent>
          </Card>
        </div>
        <div className="col-span-2">
          <Card className="h-full">
            <CardHeader><CardTitle>Recent Activity</CardTitle></CardHeader>
            <CardContent><ActivityFeed /></CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
