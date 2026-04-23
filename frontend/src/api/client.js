import { IS_PRODUCTION } from '@/lib/constants'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export async function apiFetch(path, options = {}) {
  if (IS_PRODUCTION) {
    console.warn('Write operation attempted in read-only mode:', path)
    return null
  }
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json()
}
