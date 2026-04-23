import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { InvestorRow } from './InvestorRow'
import { TIER_LABELS } from '@/lib/constants'

export function TierGroup({ tier, investors, defaultOpen = false, onRowClick }) {
  const [open, setOpen] = useState(defaultOpen)
  const contacted = investors.filter(i => !['identified','research_needed'].includes(i.pipeline_stage)).length

  return (
    <tbody>
      <tr
        className="bg-charcoal/80 cursor-pointer hover:bg-charcoal transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <td colSpan={6} className="px-4 py-2.5">
          <div className="flex items-center gap-2">
            {open ? <ChevronDown size={13} className="text-gray-500" /> : <ChevronRight size={13} className="text-gray-500" />}
            <span className="text-xs font-medium text-white">Tier {tier} — {TIER_LABELS[tier]}</span>
            <span className="font-data text-xs text-gray-500 ml-auto">
              {contacted}/{investors.length} contacted
            </span>
          </div>
        </td>
      </tr>
      {open && investors.map(inv => (
        <InvestorRow key={inv.id} investor={inv} onClick={onRowClick} />
      ))}
    </tbody>
  )
}
