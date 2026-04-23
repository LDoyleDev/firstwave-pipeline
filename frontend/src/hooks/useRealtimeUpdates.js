import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'

export function useRealtimeUpdates() {
  const qc = useQueryClient()

  useEffect(() => {
    const channel = supabase
      .channel('pipeline-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'leads' }, () => {
        qc.invalidateQueries({ queryKey: ['leads'] })
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'investor_targets' }, () => {
        qc.invalidateQueries({ queryKey: ['investors'] })
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'meetings' }, () => {
        qc.invalidateQueries({ queryKey: ['meetings'] })
      })
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [qc])
}
