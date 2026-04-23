import { useState } from 'react'
import { useAllInvestors } from '@/hooks/useInvestors'
import { TierGroup } from '@/components/investors/TierGroup'
import { InvestorDetailSheet } from '@/components/investors/InvestorDetailSheet'
import { Skeleton } from '@/components/ui/skeleton'

export default function Investors() {
  const { data: investors = [], isLoading } = useAllInvestors()
  const [selected, setSelected] = useState(null)

  if (isLoading) return <Skeleton className="h-96 w-full" />

  const byTier = [1,2,3,4,5,6].reduce((acc, t) => {
    acc[t] = investors.filter(i => i.tier === t)
    return acc
  }, {})

  return (
    <>
      <div className="mb-4 text-xs text-gray-500">
        <span className="font-data text-white">{investors.length}</span> targets across 6 tiers
      </div>
      <div className="rounded-lg border border-muted/40 overflow-hidden">
        <table className="w-full text-sm border-collapse">
          <thead className="bg-charcoal">
            <tr className="border-b border-muted/50">
              <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Firm</th>
              <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Contact</th>
              <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Stage</th>
              <th className="px-4 py-3 text-center text-xs text-gray-500 uppercase tracking-wider">Liam</th>
              <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wider">Last Contact</th>
            </tr>
          </thead>
          {[1,2,3,4,5,6].map(tier => (
            <TierGroup
              key={tier}
              tier={tier}
              investors={byTier[tier] ?? []}
              defaultOpen={tier === 1}
              onRowClick={setSelected}
            />
          ))}
        </table>
      </div>
      <InvestorDetailSheet investor={selected} onClose={() => setSelected(null)} />
    </>
  )
}
