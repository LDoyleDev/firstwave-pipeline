import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Check, X, Pencil, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { IS_PRODUCTION } from '@/lib/constants'

export function ReviewCard({ item, track, onApprove, onReject, onEdit, isActive }) {
  const [expanded, setExpanded] = useState(true)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(track === 'client' ? item.outreach_email_1 : item.outreach_draft)

  const name = track === 'client'
    ? `${item.first_name} ${item.last_name}`
    : item.firm_name

  const subtitle = track === 'client' ? item.title : `Tier ${item.tier}`

  function handleEdit() {
    if (editing) {
      onEdit?.(item.id, draft)
      setEditing(false)
    } else {
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

          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            {editing ? 'Editing Draft' : 'Outreach Draft'}
          </div>
          {editing ? (
            <textarea
              className="w-full bg-navy border border-accent/40 rounded p-3 text-xs text-gray-200 font-data leading-relaxed focus:outline-none resize-none"
              rows={10}
              value={draft}
              onChange={e => setDraft(e.target.value)}
            />
          ) : (
            <div className="bg-navy rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-data leading-relaxed">
              {draft || <span className="text-gray-600">No draft yet</span>}
            </div>
          )}

          <div className="flex gap-2 mt-3">
            <Button
              variant="success"
              size="sm"
              onClick={() => onApprove?.(item.id)}
              disabled={IS_PRODUCTION}
            >
              <Check size={13} /> Approve
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => onReject?.(item.id)}
              disabled={IS_PRODUCTION}
            >
              <X size={13} /> Reject
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleEdit}
              disabled={IS_PRODUCTION}
            >
              <Pencil size={13} /> {editing ? 'Save' : 'Edit'}
            </Button>
          </div>
          {IS_PRODUCTION && (
            <p className="text-xs text-gray-600 mt-2">Read-only — approvals require local access</p>
          )}
        </div>
      )}
    </div>
  )
}
