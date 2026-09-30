const API_BASE = import.meta.env.VITE_API_URL || '/api'
const API_KEY = import.meta.env.VITE_API_KEY

export async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  // The backend requires X-API-Key on every non-public route. The production
  // dashboard is read-only (reads go straight to Supabase) and ships no key;
  // VITE_API_KEY is set only in dev builds, where write calls hit FastAPI.
  if (API_KEY) headers['X-API-Key'] = API_KEY

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json()
}
