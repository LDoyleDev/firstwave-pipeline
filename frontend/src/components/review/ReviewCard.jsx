import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Check, X, Pencil, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

function parseJson(raw) {
  if (!raw) return null
  if (typeof raw === 'object') return raw
  try { return JSON.parse(raw) } catch { return null }
}

function normalizeSignal(s) {
  if (s && typeof s === 'object') return { text: s.text || '', url: s.source_url || null }
  if (typeof s !== 'string') return { text: String(s ?? ''), url: null }
  const m = s.match(/\(source:\s*(https?:\/\/[^)\s]+)\)/i) || s.match(/(https?:\/\/\S+)/)
  if (m) return { text: s.replace(m[0], '').trim().replace(/[,:.\s]+$/, ''), url: m[1] }
  return { text: s, url: null }
}

function EmailBlock({ to, subject, body, label }) {
  return (
    <div className="mb-3">
      {label && (
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      )}
      <div className="bg-navy rounded overflow-hidden text-xs">
        <div className="border-b border-muted/30 px-3 py-2 space-y-1">
          {to && (
            <div className="flex gap-2">
              <span className="text-gray-600 w-14 shrink-0">To</span>
              <span className="text-gray-300">{to}</span>
            </div>
          )}
          <div className="flex gap-2">
            <span className="text-gray-600 w-14 shrink-0">Subject</span>
            <span className="text-gray-200 font-medium">{subject || '(no subject)'}</span>
          </div>
        </div>
        <div className="px-3 py-2 text-gray-300 whitespace-pre-wrap leading-relaxed font-data">
          {body || '(empty body)'}
        </div>
      </div>
    </div>
  )
}

export function ReviewCard({ item, track, onApprove, onReject, onEdit, isActive }) {
  const [expanded, setExpanded] = useState(true)
  const [editing, setEditing] = useState(false)

  const rawDraft = track === 'client' ? item.outreach_email_1 : item.outreach_draft
  const parsed = parseJson(rawDraft)

  const email1 = track === 'client' ? parsed : parsed?.email_1
  const email2 = track === 'client' ? parseJson(item.outreach_email_2) : parsed?.email_2

  const recipientTo = track === 'client'
    ? (item.email || null)
    : item.contact_email
      ? (item.contact_name ? `${item.contact_name} <${item.contact_email}>` : item.contact_email)
      : (item.contact_name || null)

  const [editSubject, setEditSubject] = useState(email1?.subject || '')
  const [editBody, setEditBody] = useState(email1?.body || '')

  const name = track === 'client' ? `${item.first_name} ${item.last_name}` : item.firm_name
  const subtitle = track === 'client' ? item.title : `Tier ${item.tier}`

  function handleEdit() {
    if (editing) {
      const updated = track === 'client'
        ? JSON.stringify({ subject: editSubject, body: editBody })
        : JSON.stringify({ email_1: { subject: editSubject, body: editBody }, email_2: parsed?.email_2 || {} })
      onEdit?.(item.id, updated)
      setEditing(false)
    } else {
      setEditSubject(email1?.subject || '')
      setEditBody(email1?.body || '')
      setEditing(true)
    }
  }

  return (
    <div className={cn(
      'rounded-lg border bg-charcoal transition-colors',
      isActive ? 'border-accent/50' : 'border-muted/40',
    )}>
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-white truncate">{name}</div>
          <div className="text-xs text-gray-500">{subtitle}</div>
        </div>
        {track === 'client' && item.lead_score > 0 && (
          <Badge variant="default" className="shrink-0">Score: {item.lead_score}</Badge>
        )}
        <Badge variant={track === 'client' ? 'client' : 'investor'}>{track.toUpperCase()}</Badge>
        <button onClick={() => setExpanded(e => !e)} className="text-gray-500 hover:text-white">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-muted/30 pt-3">
          {item.pain_signals?.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {item.pain_signals.map((s, i) => <Badge key={i} variant="warning">{s}</Badge>)}
            </div>
          )}

          {(() => {
            const research = item.enrichment_data?.research
            if (!research) return null
            const dm = research.decision_maker
            const signals = (research.recent_signals || []).map(normalizeSignal)
            const hooks = research.personal_hooks || []
            const hasContent = dm?.name || signals.length > 0 || hooks.length > 0
            if (!hasContent) return null
            return (
              <div className="mb-3 bg-navy/40 rounded border border-muted/30 px-3 py-2 text-xs">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-500 uppercase tracking-wider">Research</span>
                  {typeof research.confidence === 'number' && (
                    <Badge variant={research.confidence >= 0.6 ? 'default' : 'warning'}>
                      DM conf {research.confidence.toFixed(2)}
                    </Badge>
                  )}
                </div>
                {dm?.name ? (
                  <div className="mb-2">
                    <span className="text-gray-500">Decision-maker:</span>{' '}
                    <span className="text-gray-200">{dm.name}{dm.title ? ` · ${dm.title}` : ''}</span>
                    {dm.source_url && (
                      <a href={dm.source_url} target="_blank" rel="noreferrer"
                         className="text-accent hover:underline ml-2">↗ verify</a>
                    )}
                  </div>
                ) : (
                  <div className="mb-2 text-gray-500">Decision-maker: not identified — emails address by role</div>
                )}
                {signals.length > 0 && (
                  <div className="mb-2">
                    <div className="text-gray-500 mb-1">Signals</div>
                    <ul className="space-y-1">
                      {signals.map((s, i) => (
                        <li key={i} className="flex gap-2 leading-relaxed">
                          <span className="text-gray-600 shrink-0">·</span>
                          <span className="text-gray-300 flex-1">{s.text}</span>
                          {s.url && (
                            <a href={s.url} target="_blank" rel="noreferrer"
                               className="text-accent hover:underline shrink-0">↗</a>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {hooks.length > 0 && (
                  <div>
                    <div className="text-gray-500 mb-1">Hooks</div>
                    <ul className="space-y-0.5">
                      {hooks.map((h, i) => (
                        <li key={i} className="text-gray-300 leading-relaxed">· {h}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {research.notes && (
                  <div className="mt-2 text-gray-600 italic">{research.notes}</div>
                )}
              </div>
            )
          })()}

          {editing ? (
            <div className="space-y-2 mb-3">
              <div className="text-xs text-gray-500 uppercase tracking-wider">Editing Email 1</div>
              <div className="flex gap-2 items-center">
                <span className="text-xs text-gray-600 w-14 shrink-0">Subject</span>
                <input
                  className="flex-1 bg-navy border border-accent/40 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none"
                  value={editSubject}
                  onChange={e => setEditSubject(e.target.value)}
                />
              </div>
              <textarea
                className="w-full bg-navy border border-accent/40 rounded p-3 text-xs text-gray-200 font-data leading-relaxed focus:outline-none resize-none"
                rows={10}
                value={editBody}
                onChange={e => setEditBody(e.target.value)}
              />
            </div>
          ) : (
            <div>
              <EmailBlock
                label={email2 ? 'Email 1' : undefined}
                to={recipientTo}
                subject={email1?.subject}
                body={email1?.body}
              />
              {email2 && (
                <EmailBlock
                  label="Email 2"
                  to={recipientTo}
                  subject={email2.subject}
                  body={email2.body}
                />
              )}
              {!email1 && (
                <div className="bg-navy rounded p-3 text-xs text-gray-600">No draft yet</div>
              )}
            </div>
          )}

          <div className="flex gap-2 mt-3">
            <Button variant="success" size="sm" onClick={() => onApprove?.(item.id)}>
              <Check size={13} /> Approve
            </Button>
            <Button variant="danger" size="sm" onClick={() => onReject?.(item.id)}>
              <X size={13} /> Reject
            </Button>
            <Button variant="outline" size="sm" onClick={handleEdit}>
              <Pencil size={13} /> {editing ? 'Save' : 'Edit'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
