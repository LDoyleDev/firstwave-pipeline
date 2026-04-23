import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { updateMeeting } from '@/api/meetings'

export function useMeetingsToday() {
  return useQuery({
    queryKey: ['meetings', 'today'],
    queryFn: async () => {
      const today = new Date().toLocaleDateString('sv', { timeZone: 'Europe/Berlin' })
      const start = `${today}T00:00:00`
      const end   = `${today}T23:59:59`
      const { data, error } = await supabase
        .from('meetings')
        .select('*, leads(*), investor_targets(*)')
        .gte('scheduled_at', start)
        .lte('scheduled_at', end)
      if (error) throw error
      const slots = [1, 2, 3].map((n) => ({
        slot: n,
        time: ['10:30', '10:50', '11:10'][n - 1],
        meeting: (data ?? []).find((m) => m.slot_number === n) ?? null,
      }))
      return { date: today, slots, available_slots: slots.filter((s) => !s.meeting).length }
    },
    refetchInterval: 30000,
  })
}

export function useMeetings(dateFilter) {
  return useQuery({
    queryKey: ['meetings', dateFilter],
    queryFn: async () => {
      let q = supabase
        .from('meetings')
        .select('*, leads(*), investor_targets(*)')
        .order('scheduled_at')
      if (dateFilter) {
        q = q.gte('scheduled_at', `${dateFilter}T00:00:00`).lte('scheduled_at', `${dateFilter}T23:59:59`)
      }
      const { data, error } = await q
      if (error) throw error
      return data ?? []
    },
  })
}

export function useUpdateMeeting() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => updateMeeting(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meetings'] }),
  })
}
