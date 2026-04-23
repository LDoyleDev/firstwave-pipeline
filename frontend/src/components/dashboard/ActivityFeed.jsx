import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { formatDistanceToNow } from 'date-fns'
import { Users, TrendingUp, Calendar } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'

async function fetchActivity() {
  const [{ data: leads }, { data: investors }, { data: meetings }] = await Promise.all([
    supabase.from('leads').select('id,first_name,last_name,pipeline_stage,updated_at').order('updated_at', { ascending: false }).limit(5),
    supabase.from('investor_targets').select('id,firm_name,pipeline_stage,updated_at').order('updated_at', { ascending: false }).limit(5),
    supabase.from('meetings').select('id,track,status,outcome,scheduled_at,updated_at,leads(first_name,last_name),investor_targets(firm_name)').order('updated_at', { ascending: false }).limit(5),
  ])
  const items = [
    ...(leads  ?? []).map(r => ({ type: 'lead',     at: r.updated_at, icon: Users,       text: `${r.first_name} ${r.last_name} → ${r.pipeline_stage.replace('_',' ')}` })),
    ...(investors ?? []).map(r => ({ type: 'investor', at: r.updated_at, icon: TrendingUp,  text: `${r.firm_name} → ${r.pipeline_stage.replace('_',' ')}` })),
    ...(meetings  ?? []).map(r => ({ type: 'meeting',  at: r.updated_at, icon: Calendar,    text: `Meeting ${r.status}: ${r.leads ? `${r.leads.first_name} ${r.leads.last_name}` : r.investor_targets?.firm_name ?? '—'}` })),
  ]
  return items.sort((a, b) => new Date(b.at) - new Date(a.at)).slice(0, 10)
}

export function ActivityFeed() {
  const { data, isLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: fetchActivity,
    refetchInterval: 30000,
  })

  if (isLoading) return <div className="space-y-3">{[...Array(5)].map((_,i) => <Skeleton key={i} className="h-8" />)}</div>

  if (!data?.length) return (
    <div className="text-center py-8 text-gray-600 text-sm">No activity yet</div>
  )

  return (
    <div className="space-y-1">
      {data.map((item, i) => (
        <div key={i} className="flex items-start gap-3 py-2 border-b border-muted/30 last:border-0">
          <item.icon size={13} className="text-gray-500 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-gray-300 truncate">{item.text}</div>
            <div className="text-xs text-gray-600 mt-0.5 font-data">
              {formatDistanceToNow(new Date(item.at), { addSuffix: true })}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
