import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { apiFetch } from '@/api/client'

const MARKETS = ['UK', 'DACH', 'Australia', 'UAE', 'Ireland', 'NZ', 'SouthAfrica', 'Singapore', 'India', 'HongKong', 'EastAfrica', 'WestAfrica', 'Philippines', 'MaltaCaribbean']

function ActionButton({ label, count, loading, disabled, onClick, variant = 'default' }) {
  const base = 'flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed'
  const styles = {
    default: 'bg-gray-700 hover:bg-gray-600 text-white',
    primary: 'bg-blue-600 hover:bg-blue-500 text-white',
    warning: 'bg-amber-600 hover:bg-amber-500 text-white',
  }
  return (
    <button
      className={`${base} ${styles[variant]}`}
      onClick={onClick}
      disabled={loading || disabled}
    >
      {loading ? (
        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      ) : null}
      {label}
      {count != null && !loading && (
        <span className="ml-1 px-1.5 py-0.5 text-xs bg-white/15 rounded-full">{count}</span>
      )}
    </button>
  )
}

export function ActionPanel() {
  const qc = useQueryClient()
  const [loadingKey, setLoadingKey] = useState(null)
  const [message, setMessage] = useState(null)
  const [findDropdownOpen, setFindDropdownOpen] = useState(false)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['action-queue-stats'],
    queryFn: () => apiFetch('/actions/queue-stats'),
    refetchInterval: 30000,
  })

  const run = async (key, path, body) => {
    setLoadingKey(key)
    setMessage(null)
    try {
      const result = await apiFetch(path, {
        method: body ? 'POST' : 'GET',
        body: body ? JSON.stringify(body) : undefined,
      })
      const msg = result?.message
        || (result?.added != null ? `Found ${result.found}, added ${result.added}` : null)
        || (result?.succeeded != null ? `Processed ${result.processed}, ${result.succeeded} succeeded` : null)
        || 'Done'
      setMessage({ type: 'success', text: msg })
      qc.invalidateQueries({ queryKey: ['action-queue-stats'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
    } catch (e) {
      setMessage({ type: 'error', text: String(e.message || e) })
    } finally {
      setLoadingKey(null)
    }
  }

  const handleDiscover = (market) => {
    setFindDropdownOpen(false)
    run('discover', '/actions/discover', { market, max_pages: 4 })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-center gap-3">

          {/* Find Leads with market dropdown */}
          <div className="relative">
            <ActionButton
              label="Find Leads"
              loading={loadingKey === 'discover'}
              onClick={() => setFindDropdownOpen(v => !v)}
              variant="default"
            />
            {findDropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-44 bg-gray-800 border border-gray-700 rounded shadow-lg z-10">
                {MARKETS.map(m => (
                  <button
                    key={m}
                    className="w-full text-left px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 first:rounded-t last:rounded-b"
                    onClick={() => handleDiscover(m)}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Enrich Queue */}
          <ActionButton
            label="Enrich Queue"
            count={statsLoading ? null : stats?.discovered_unenriched}
            loading={loadingKey === 'enrich'}
            disabled={!stats?.discovered_unenriched}
            onClick={() => run('enrich', '/actions/enrich-batch', { batch_size: 5 })}
            variant="primary"
          />

          {/* Prepare Outreach */}
          <ActionButton
            label="Prepare Outreach"
            count={statsLoading ? null : stats?.enriched_no_draft}
            loading={loadingKey === 'outreach'}
            disabled={!stats?.enriched_no_draft}
            onClick={() => run('outreach', '/actions/generate-outreach-batch', { batch_size: 10, track: 'client' })}
            variant="warning"
          />

          {/* Daily sends indicator */}
          {stats && (
            <span className="ml-auto text-xs text-gray-500">
              Sent today: {stats.daily_sends_today}/{stats.daily_limit}
            </span>
          )}
        </div>

        {/* Status message */}
        {message && (
          <div className={`mt-3 text-sm px-3 py-2 rounded ${
            message.type === 'success' ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'
          }`}>
            {message.text}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
