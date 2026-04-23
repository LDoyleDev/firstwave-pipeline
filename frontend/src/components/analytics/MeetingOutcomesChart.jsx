import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'
import { OUTCOME_COLORS } from '@/lib/constants'
import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'

export function MeetingOutcomesChart() {
  const { data = [] } = useQuery({
    queryKey: ['meetings-outcomes'],
    queryFn: async () => {
      const { data } = await supabase.from('meetings').select('outcome').not('outcome', 'is', null)
      if (!data?.length) return []
      const counts = {}
      data.forEach(m => { counts[m.outcome] = (counts[m.outcome] ?? 0) + 1 })
      return Object.entries(counts).map(([name, value]) => ({ name, value }))
    },
  })

  if (!data.length) return (
    <div className="h-48 flex items-center justify-center text-gray-600 text-sm">No meeting outcomes yet</div>
  )

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
          {data.map((entry, i) => <Cell key={i} fill={OUTCOME_COLORS[entry.name] ?? '#374151'} />)}
        </Pie>
        <Tooltip contentStyle={{ backgroundColor: '#1a1d2e', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }} />
        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
