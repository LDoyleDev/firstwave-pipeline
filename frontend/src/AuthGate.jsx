import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'

// Single-operator tool: one shared Supabase Auth account. The email is fixed
// (configure via VITE_AUTH_EMAIL); the operator only types the password.
// The account itself is created in the Supabase dashboard, and public sign-up
// MUST be disabled there — otherwise anyone could self-register into the
// `authenticated` role and read every RLS-protected table.
const AUTH_EMAIL = import.meta.env.VITE_AUTH_EMAIL || 'liam@firstwaveai.com'

export function AuthGate({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    // Restore an existing session (Supabase persists it in localStorage).
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })
    // React to sign-in / sign-out anywhere in the app (e.g. the TopBar logout).
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, sess) => {
      setSession(sess)
    })
    return () => subscription.unsubscribe()
  }, [])

  // Blank navy screen while the session check resolves — avoids a login-form flash.
  if (loading) return <div className="min-h-screen bg-navy" />

  if (session) return children

  async function submit(e) {
    e.preventDefault()
    setSubmitting(true)
    setErr('')
    const { error } = await supabase.auth.signInWithPassword({
      email: AUTH_EMAIL,
      password,
    })
    setSubmitting(false)
    if (error) {
      // Show the real message — helps distinguish a wrong password from a
      // missing account or disabled email logins during setup.
      setErr(error.message)
      setPassword('')
    }
    // On success, onAuthStateChange flips `session` and the app renders.
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
            placeholder="Operator password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setErr('') }}
            autoFocus
            className="w-full rounded border border-muted bg-navy px-4 py-3 text-sm text-white placeholder-gray-600 focus:border-accent focus:outline-none transition-colors"
          />
          {err && <p className="text-xs text-red-400">{err}</p>}
          <button
            type="submit"
            disabled={submitting || !password}
            className="w-full bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white rounded py-3 text-sm font-medium transition-colors"
          >
            {submitting ? 'Signing in…' : 'Enter'}
          </button>
        </form>
        <p className="mt-4 text-center text-xs text-gray-600">{AUTH_EMAIL}</p>
      </div>
    </div>
  )
}
