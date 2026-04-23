import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { updateInvestor, approveInvestor, rejectInvestor } from '@/api/investors'

export function useInvestors(tier, stage) {
  return useQuery({
    queryKey: ['investors', tier, stage],
    queryFn: async () => {
      let q = supabase.from('investor_targets').select('*').order('tier').order('firm_name')
      if (tier)  q = q.eq('tier', tier)
      if (stage) q = q.eq('pipeline_stage', stage)
      const { data, error } = await q
      if (error) throw error
      return data ?? []
    },
    refetchInterval: 30000,
  })
}

export function useAllInvestors() {
  return useInvestors(undefined, undefined)
}

export function useUpdateInvestor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => updateInvestor(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['investors'] }),
  })
}

export function useApproveInvestor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => approveInvestor(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['investors'] }),
  })
}

export function useRejectInvestor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => rejectInvestor(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['investors'] }),
  })
}
