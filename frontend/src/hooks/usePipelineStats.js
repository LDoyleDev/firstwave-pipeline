import { useMemo } from 'react'
import { useAllLeads } from './useLeads'
import { useAllInvestors } from './useInvestors'
import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { startOfWeek } from 'date-fns'

export function usePipelineStats() {
  const { data: leads = [] }     = useAllLeads()
  const { data: investors = [] } = useAllInvestors()

  const reviewQueue = useQuery({
    queryKey: ['review-queue'],
    queryFn: async () => {
      const { data: l } = await supabase.from('leads').select('id').eq('outreach_approved', false).not('outreach_email_1', 'is', null)
      const { data: i } = await supabase.from('investor_targets').select('id').eq('outreach_approved', false).not('outreach_draft', 'is', null)
      return { leads: l?.length ?? 0, investors: i?.length ?? 0 }
    },
    refetchInterval: 30000,
  })

  const sequences = useQuery({
    queryKey: ['sequences-active'],
    queryFn: async () => {
      const { count } = await supabase.from('email_sequences').select('id', { count: 'exact', head: true }).eq('status', 'sent')
      return count ?? 0
    },
    refetchInterval: 30000,
  })

  const repliesThisWeek = useMemo(() => {
    const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 })
    const count = [...leads, ...investors].filter((r) => {
      if (r.pipeline_stage !== 'replied') return false
      const updated = new Date(r.updated_at)
      return updated >= weekStart
    }).length
    return count
  }, [leads, investors])

  const meetingsThisWeek = useQuery({
    queryKey: ['meetings-this-week'],
    queryFn: async () => {
      const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 }).toISOString()
      const { count } = await supabase
        .from('meetings')
        .select('id', { count: 'exact', head: true })
        .eq('status', 'completed')
        .gte('scheduled_at', weekStart)
      return count ?? 0
    },
    refetchInterval: 30000,
  })

  const clientStageCounts = useMemo(() => {
    const counts = {}
    leads.forEach((l) => { counts[l.pipeline_stage] = (counts[l.pipeline_stage] ?? 0) + 1 })
    return counts
  }, [leads])

  const investorStageCounts = useMemo(() => {
    const counts = {}
    investors.forEach((i) => { counts[i.pipeline_stage] = (counts[i.pipeline_stage] ?? 0) + 1 })
    return counts
  }, [investors])

  return {
    reviewQueue: {
      leads: reviewQueue.data?.leads ?? 0,
      investors: reviewQueue.data?.investors ?? 0,
      total: (reviewQueue.data?.leads ?? 0) + (reviewQueue.data?.investors ?? 0),
    },
    activeInSequence: sequences.data ?? 0,
    repliesThisWeek,
    meetingsThisWeek: meetingsThisWeek.data ?? 0,
    clientStageCounts,
    investorStageCounts,
    totalLeads: leads.length,
    totalInvestors: investors.length,
  }
}
