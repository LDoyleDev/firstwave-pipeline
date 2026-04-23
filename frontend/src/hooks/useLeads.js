import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { updateLead, approveLead, rejectLead, enrichLead, generateOutreach } from '@/api/leads'

export function useLeads(stage) {
  return useQuery({
    queryKey: ['leads', stage],
    queryFn: async () => {
      let q = supabase.from('leads').select('*').order('created_at', { ascending: false })
      if (stage) q = q.eq('pipeline_stage', stage)
      const { data, error } = await q
      if (error) throw error
      return data ?? []
    },
    refetchInterval: 30000,
  })
}

export function useAllLeads() {
  return useLeads(undefined)
}

export function useUpdateLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => updateLead(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })
}

export function useApproveLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => approveLead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })
}

export function useRejectLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => rejectLead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })
}

export function useEnrichLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => enrichLead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })
}

export function useGenerateOutreach() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => generateOutreach(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })
}
