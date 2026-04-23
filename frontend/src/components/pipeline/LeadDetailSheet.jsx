import { Sheet } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { WARMTH_COLORS } from '@/lib/constants'

function Field({ label, value }) {
  if (!value) return null
  return (
    <div className="mb-3">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm text-gray-200">{value}</div>
    </div>
  )
}

export function LeadDetailSheet({ lead, onClose }) {
  if (!lead) return null
  return (
    <Sheet open={!!lead} onClose={onClose} title={`${lead.first_name} ${lead.last_name}`}>
      <div className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={lead.warmth ?? 'cold'}>{lead.warmth?.toUpperCase() ?? 'COLD'}</Badge>
          {lead.lead_score > 0 && <Badge variant="default">Score: {lead.lead_score}</Badge>}
          <Badge variant="muted">{lead.pipeline_stage?.replace('_',' ')}</Badge>
        </div>

        <Field label="Title" value={lead.title} />
        <Field label="Email" value={lead.email} />
        <Field label="Location" value={lead.location} />
        <Field label="Source" value={lead.source} />

        {lead.pain_signals?.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Pain Signals</div>
            <div className="flex flex-wrap gap-1">
              {lead.pain_signals.map((s, i) => <Badge key={i} variant="warning">{s}</Badge>)}
            </div>
          </div>
        )}

        {lead.personalisation_hooks?.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Hooks</div>
            <div className="flex flex-wrap gap-1">
              {lead.personalisation_hooks.map((h, i) => <Badge key={i} variant="default">{h}</Badge>)}
            </div>
          </div>
        )}

        {lead.outreach_email_1 && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Email 1 Draft</div>
            <div className="bg-navy rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-data leading-relaxed">
              {lead.outreach_email_1}
            </div>
          </div>
        )}

        {lead.outreach_email_2 && (
          <div className="mt-4">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Email 2 Draft</div>
            <div className="bg-navy rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-data leading-relaxed">
              {lead.outreach_email_2}
            </div>
          </div>
        )}

        <Field label="Notes" value={lead.notes} />
        <Field label="LinkedIn" value={lead.linkedin_url} />
      </div>
    </Sheet>
  )
}
