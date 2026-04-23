import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDistanceToNow, parseISO } from 'date-fns'

function StatusBadge({ status }) {
  const v = { processed: 'success', failed: 'danger', pending_confirmation: 'warning' }
  return <Badge variant={v[status] ?? 'muted'}>{status}</Badge>
}

export default function Voice() {
  const { data: commands = [], isLoading } = useQuery({
    queryKey: ['voice-commands'],
    queryFn: async () => {
      const { data } = await supabase
        .from('voice_commands')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50)
      return data ?? []
    },
    refetchInterval: 30000,
  })

  if (isLoading) return <Skeleton className="h-96 w-full" />

  if (!commands.length) return (
    <div className="text-center py-20 text-gray-600 text-sm">
      No voice commands yet — send a voice note via Telegram to get started
    </div>
  )

  return (
    <div className="rounded-lg border border-muted/40 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-charcoal">
          <tr className="border-b border-muted/50">
            <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Time</th>
            <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Transcript</th>
            <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Intent</th>
            <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Action</th>
            <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody>
          {commands.map(cmd => {
            let intent = null
            try { intent = JSON.parse(cmd.parsed_intent) } catch {}
            return (
              <tr key={cmd.id} className="border-b border-muted/30 hover:bg-muted/10 transition-colors">
                <td className="px-4 py-3 text-xs text-gray-500 font-data whitespace-nowrap">
                  {formatDistanceToNow(parseISO(cmd.created_at), { addSuffix: true })}
                </td>
                <td className="px-4 py-3 text-xs text-gray-300 max-w-xs truncate">{cmd.raw_transcript}</td>
                <td className="px-4 py-3">
                  {intent?.intent ? <Badge variant="default">{intent.intent}</Badge> : <span className="text-gray-600">—</span>}
                </td>
                <td className="px-4 py-3 text-xs text-gray-400 max-w-xs truncate">{cmd.action_taken}</td>
                <td className="px-4 py-3"><StatusBadge status={cmd.status} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
