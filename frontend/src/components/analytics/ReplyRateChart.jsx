import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'
import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { format, subWeeks, startOfWeek, endOfWeek } from 'date-fns'

export function ReplyRateChart() {
  const { data = [] } = useQuery({
    queryKey: ['reply-rate-weekly'],
    queryFn: async () => {
      const weeks = Array.from({ length: 8 }, (_, i) => {
        const start = startOfWeek(subWeeks(new Date(), 7 - i), { weekStartsOn: 1 })
        const end   = endOfWeek(start, { weekStartsOn: 1 })
        return { label: format(start, 'MMM d'), start: start.toISOString(), end: end.toISOString() }
      })
      const rows = await Promise.all(weeks.map(async ({ label, start, end }) => {
        const [{ count: sent }, { count: replied }] = await Promise.all([
          supabase.from('email_sequences').select('id', { count: 'exact', head: true }).gte('sent_at', start).lte('sent_at', end),
          supabase.from('leads').select('id', { count: 'exact', head: true }).eq('pipeline_stage','replied').gte('updated_at', start).lte('updated_at', end),
        ])
        return { week: label, Sent: sent ?? 0, Replies: replied ?? 0 }
      }))
      return rows
    },
  })

  const tooltipStyle = { backgroundColor: '#1a1d2e', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }
  const labelStyle = { fill: '#9ca3af', fontSize: 11 }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
        <CartesianGrid stroke="#374151" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="week" tick={labelStyle} axisLine={false} tickLine={false} />
        <YAxis tick={labelStyle} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: '#9ca3af' }} />
        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
        <Line type="monotone" dataKey="Sent"    stroke="#2563eb" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Replies" stroke="#22c55e" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
