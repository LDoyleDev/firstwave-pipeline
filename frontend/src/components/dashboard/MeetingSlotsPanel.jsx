import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useMeetingsToday } from '@/hooks/useMeetings'
import { Skeleton } from '@/components/ui/skeleton'

const OUTCOME_BADGE = { hot: 'hot', warm: 'warm', cold: 'cold', dead: 'muted', won: 'success' }

export function MeetingSlotsPanel() {
  const { data, isLoading } = useMeetingsToday()

  if (isLoading) return (
    <div className="grid grid-cols-3 gap-4">
      {[1,2,3].map(n => <Skeleton key={n} className="h-36" />)}
    </div>
  )

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-3">
        <span className="text-xs text-gray-500 uppercase tracking-widest">Today — {data?.date}</span>
        <span className="font-data text-xs text-gray-600">{data?.available_slots ?? 3} slots available</span>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {(data?.slots ?? [{slot:1,time:'10:30',meeting:null},{slot:2,time:'10:50',meeting:null},{slot:3,time:'11:10',meeting:null}]).map(({ slot, time, meeting }) => {
          const isPast = (() => {
            const now = new Date()
            const [h, m] = time.split(':').map(Number)
            const slotDate = new Date(now)
            slotDate.setHours(h, m + 20, 0)
            return now > slotDate
          })()

          return (
            <Card key={slot} className={cn(
              'relative overflow-hidden',
              meeting ? 'border-accent/40' : isPast ? 'border-muted/30 opacity-50' : 'border-green-500/30',
            )}>
              <div className="p-4">
                <div className="font-data text-xl font-medium text-white mb-1">{time}</div>
                {meeting ? (
                  <>
                    <div className="text-sm font-medium text-white truncate">
                      {meeting.leads
                        ? `${meeting.leads.first_name} ${meeting.leads.last_name}`
                        : meeting.investor_targets?.firm_name ?? '—'}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5 truncate">
                      {meeting.leads?.title ?? meeting.investor_targets?.investor_type ?? ''}
                    </div>
                    <div className="flex items-center gap-2 mt-3">
                      <Badge variant={meeting.track === 'client' ? 'client' : 'investor'}>
                        {meeting.track?.toUpperCase()}
                      </Badge>
                      {meeting.outcome && (
                        <Badge variant={OUTCOME_BADGE[meeting.outcome] ?? 'muted'}>
                          {meeting.outcome.toUpperCase()}
                        </Badge>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex items-center gap-2 mt-2">
                    {!isPast && <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />}
                    <span className={cn('text-sm font-data', isPast ? 'text-gray-600' : 'text-green-400')}>
                      {isPast ? 'EMPTY' : 'AVAILABLE'}
                    </span>
                  </div>
                )}
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
