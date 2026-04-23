import { Badge } from '@/components/ui/badge'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { cn } from '@/lib/utils'

const STAGE_VARIANTS = {
  identified: 'muted', research_needed: 'muted', ready_to_contact: 'warning',
  contacted: 'default', replied: 'success', meeting_booked: 'client',
  met: 'success', term_sheet: 'investor', closed: 'success', pass: 'danger',
}

export function InvestorRow({ investor, onClick }) {
  return (
    <tr
      className="border-b border-muted/30 hover:bg-muted/10 cursor-pointer transition-colors"
      onClick={() => onClick?.(investor)}
    >
      <td className="px-4 py-3 text-sm font-medium text-white">{investor.firm_name}</td>
      <td className="px-4 py-3 text-xs text-gray-400">{investor.investor_type}</td>
      <td className="px-4 py-3 text-xs text-gray-400">{investor.contact_name || <span className="text-gray-600">—</span>}</td>
      <td className="px-4 py-3">
        <Badge variant={STAGE_VARIANTS[investor.pipeline_stage] ?? 'muted'}>
          {investor.pipeline_stage?.replace('_',' ')}
        </Badge>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={cn('font-data text-sm', investor.liam_leads ? 'text-accent' : 'text-gray-600')}>
          {investor.liam_leads ? '●' : '○'}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-gray-500 font-data">
        {investor.last_contacted_at
          ? formatDistanceToNow(parseISO(investor.last_contacted_at), { addSuffix: true })
          : <span className="text-gray-700">—</span>}
      </td>
    </tr>
  )
}
