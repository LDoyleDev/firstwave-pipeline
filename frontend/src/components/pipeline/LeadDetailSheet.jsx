import { Sheet } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { useEnrichLead, useGenerateOutreach } from '@/hooks/useLeads'

function Field({ label, value }) {
  if (!value) return null
  return (
    <div className="mb-3">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm text-gray-200">{value}</div>
    </div>
  )
}

function parseEmail(raw) {
  if (!raw) return null
  if (typeof raw === 'object') return raw
  try { return JSON.parse(raw) } catch { return { body: raw } }
}

function EmailDraft({ label, raw }) {
  const email = parseEmail(raw)
  if (!email) return null
  return (
    <div>
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">{label}</div>
      {email.subject && (
        <div className="text-xs text-gray-400 mb-1 font-medium">Subject: {email.subject}</div>
      )}
      <div className="bg-navy rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-data leading-relaxed">
        {email.body}
      </div>
    </div>
  )
}

export function LeadDetailSheet({ lead, onClose }) {
  const enrich = useEnrichLead()
  const genOutreach = useGenerateOutreach()

  if (!lead) return null

  const isEnriched = !!lead.enrichment_data
  const hasEmails = !!lead.outreach_email_1

  return (
    <Sheet open={!!lead} onClose={onClose} title={`${lead.first_name} ${lead.last_name}`}>
      <div className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={lead.warmth ?? 'cold'}>{lead.warmth?.toUpperCase() ?? 'COLD'}</Badge>
          {lead.lead_score > 0 && <Badge variant="default">Score: {lead.lead_score}</Badge>}
          <Badge variant="muted">{lead.pipeline_stage?.replace('_', ' ')}</Badge>
        </div>

        <div className="flex gap-2 flex-wrap">
          {!isEnriched && (
            <button
              onClick={() => enrich.mutate(lead.id)}
              disabled={enrich.isPending}
              className="px-3 py-1.5 text-xs rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium transition-colors"
            >
              {enrich.isPending ? 'Enriching…' : 'Enrich'}
            </button>
          )}
          {isEnriched && !hasEmails && (
            <button
              onClick={() => genOutreach.mutate(lead.id)}
              disabled={genOutreach.isPending}
              className="px-3 py-1.5 text-xs rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium transition-colors"
            >
              {genOutreach.isPending ? 'Preparing…' : 'Prepare Emails'}
            </button>
          )}
          {enrich.isError && (
            <span className="text-xs text-red-400">Enrichment failed — try again</span>
          )}
          {genOutreach.isError && (
            <span className="text-xs text-red-400">Email generation failed — try again</span>
          )}
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

        <EmailDraft label="Email 1 Draft" raw={lead.outreach_email_1} />
        {lead.outreach_email_2 && <EmailDraft label="Email 2 Draft" raw={lead.outreach_email_2} />}

        <Field label="Notes" value={lead.notes} />
        <Field label="LinkedIn" value={lead.linkedin_url} />
      </div>
    </Sheet>
  )
}
