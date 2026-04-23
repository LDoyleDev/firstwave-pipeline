import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { ReviewCard } from '@/components/review/ReviewCard'
import { useApproveLead, useRejectLead, useUpdateLead } from '@/hooks/useLeads'
import { useApproveInvestor, useRejectInvestor, useUpdateInvestor } from '@/hooks/useInvestors'
import { Skeleton } from '@/components/ui/skeleton'

function useReviewQueue() {
  return useQuery({
    queryKey: ['review-queue', 'full'],
    queryFn: async () => {
      const [{ data: leads }, { data: investors }] = await Promise.all([
        supabase.from('leads').select('*').eq('outreach_approved', false).not('outreach_email_1', 'is', null).order('lead_score', { ascending: false }),
        supabase.from('investor_targets').select('*').eq('outreach_approved', false).not('outreach_draft', 'is', null).order('tier'),
      ])
      return { leads: leads ?? [], investors: investors ?? [] }
    },
    refetchInterval: 30000,
  })
}

export default function Review() {
  const { data, isLoading } = useReviewQueue()
  const [activeIdx, setActiveIdx] = useState({ client: 0, investor: 0 })
  const approveLead = useApproveLead()
  const rejectLead  = useRejectLead()
  const updateLead  = useUpdateLead()
  const approveInv  = useApproveInvestor()
  const rejectInv   = useRejectInvestor()
  const updateInv   = useUpdateInvestor()

  useEffect(() => {
    function onKey(e) {
      if (e.target.tagName === 'TEXTAREA') return
      if (e.key === 'ArrowRight') setActiveIdx(p => ({ ...p, client: Math.min(p.client + 1, (data?.leads?.length ?? 1) - 1) }))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [data])

  if (isLoading) return <Skeleton className="h-96 w-full" />

  const { leads = [], investors = [] } = data ?? {}

  return (
    <div>
      <div className="mb-4 text-xs text-gray-500">
        <span className="font-data text-white">{leads.length + investors.length}</span> pending approvals
        {' '}(<span className="font-data">{leads.length}</span> client, <span className="font-data">{investors.length}</span> investor)
        <span className="ml-4 text-gray-700">A = approve · R = reject · E = edit</span>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-3">
            Client Queue <span className="font-data text-white ml-1">{leads.length}</span>
          </div>
          {leads.length === 0
            ? <div className="text-center py-12 text-gray-600 text-sm border border-muted/30 rounded-lg">Queue empty</div>
            : <div className="space-y-3">
                {leads.map((lead, i) => (
                  <ReviewCard
                    key={lead.id}
                    item={lead}
                    track="client"
                    isActive={i === activeIdx.client}
                    onApprove={id => approveLead.mutate(id)}
                    onReject={id => rejectLead.mutate(id)}
                    onEdit={(id, draft) => updateLead.mutate({ id, data: { outreach_email_1: draft } })}
                  />
                ))}
              </div>
          }
        </div>

        <div>
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-3">
            Investor Queue <span className="font-data text-white ml-1">{investors.length}</span>
          </div>
          {investors.length === 0
            ? <div className="text-center py-12 text-gray-600 text-sm border border-muted/30 rounded-lg">Queue empty</div>
            : <div className="space-y-3">
                {investors.map((inv, i) => (
                  <ReviewCard
                    key={inv.id}
                    item={inv}
                    track="investor"
                    isActive={i === activeIdx.investor}
                    onApprove={id => approveInv.mutate(id)}
                    onReject={id => rejectInv.mutate(id)}
                    onEdit={(id, draft) => updateInv.mutate({ id, data: { outreach_draft: draft } })}
                  />
                ))}
              </div>
          }
        </div>
      </div>
    </div>
  )
}
