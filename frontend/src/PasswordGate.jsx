import { useState } from 'react'

const PASS = import.meta.env.VITE_ACCESS_PASSWORD || 'firstwave2026'
const KEY  = 'fw_auth'

function hash(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0
  return String(h)
}

export function PasswordGate({ children }) {
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname.startsWith('192.168') || window.location.hostname.startsWith('100.') || window.location.hostname.endsWith('.ts.net')
  const [authed, setAuthed] = useState(() => isLocal || localStorage.getItem(KEY) === hash(PASS))
  const [val, setVal] = useState('')
  const [err, setErr]  = useState(false)

  if (authed) return children

  function submit(e) {
    e.preventDefault()
    if (hash(val) === hash(PASS)) {
      localStorage.setItem(KEY, hash(PASS))
      setAuthed(true)
    } else {
      setErr(true)
      setVal('')
    }
  }

  return (
    <div className="min-h-screen bg-navy flex items-center justify-center">
      <div className="w-full max-w-sm bg-charcoal border border-muted/50 rounded-lg p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="text-xs font-data font-medium text-accent tracking-widest uppercase mb-1">FirstWave</div>
          <div className="text-white font-medium">Pipeline Access</div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <input
            type="password"
            placeholder="Access password"
            value={val}
            onChange={(e) => { setVal(e.target.value); setErr(false) }}
            autoFocus
            className="w-full rounded border border-muted bg-navy px-4 py-3 text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none transition-colors"
          />
          {err && <p className="text-xs text-red-400">Incorrect password</p>}
          <button
            type="submit"
            className="w-full bg-accent hover:bg-accent-hover text-white rounded py-3 text-sm font-medium transition-colors"
          >
            Enter
          </button>
        </form>
      </div>
    </div>
  )
}
