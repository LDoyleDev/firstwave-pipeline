import { useState } from 'react'
import { addDays, startOfWeek, format, isSameDay, isToday } from 'date-fns'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SlotCell } from '@/components/meetings/SlotCell'
import { useMeetings } from '@/hooks/useMeetings'
import { cn } from '@/lib/utils'

const SLOTS = [
  { n: 1, time: '10:30' },
  { n: 2, time: '10:50' },
  { n: 3, time: '11:10' },
]

export default function Meetings() {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  const { data: meetings = [] } = useMeetings()

  function getMeeting(day, slotNum) {
    return meetings.find(m => {
      const at = new Date(m.scheduled_at)
      return isSameDay(at, day) && m.slot_number === slotNum
    }) ?? null
  }

  function isPastSlot(day, time) {
    const now = new Date()
    const [h, m] = time.split(':').map(Number)
    const slotEnd = new Date(day)
    slotEnd.setHours(h, m + 20, 0)
    return now > slotEnd
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <Button variant="ghost" size="icon" onClick={() => setWeekStart(d => addDays(d, -7))}>
          <ChevronLeft size={16} />
        </Button>
        <span className="text-sm text-white font-medium">
          {format(weekStart, 'MMM d')} – {format(addDays(weekStart, 6), 'MMM d, yyyy')}
        </span>
        <Button variant="ghost" size="icon" onClick={() => setWeekStart(d => addDays(d, 7))}>
          <ChevronRight size={16} />
        </Button>
        <Button variant="outline" size="sm" onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))}>
          This week
        </Button>
      </div>

      <div className="grid grid-cols-7 gap-2">
        {days.map(day => (
          <div key={day.toISOString()} className={cn(
            'rounded-lg border p-3',
            isToday(day) ? 'border-accent/40 bg-accent/5' : 'border-muted/30',
          )}>
            <div className="text-center mb-3">
              <div className="text-xs text-gray-500">{format(day, 'EEE')}</div>
              <div className={cn('text-lg font-data', isToday(day) ? 'text-accent' : 'text-white')}>
                {format(day, 'd')}
              </div>
            </div>
            <div className="space-y-1.5">
              {SLOTS.map(({ n, time }) => (
                <SlotCell
                  key={n}
                  slot={n}
                  time={time}
                  meeting={getMeeting(day, n)}
                  isPast={isPastSlot(day, time)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
