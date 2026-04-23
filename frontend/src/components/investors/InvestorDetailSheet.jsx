import { Sheet } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { TIER_LABELS } from '@/lib/constants'
import { useEnrichInvestor, useGenerateInvestorOutreach } from '@/hooks/useInvestors'

function Field({ label, value }) {
  if (!value) return null
  return (
    <div className="mb-3">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm text-gray-200">{value}</div>
    </div>
  )
}

function parseOutreachDraft(raw) {
  if (!raw) return null
  if (typeof raw === 'object') return raw
  try { return JSON.parse(raw) } catch { return null }
}

function EmailDraft({ label, subject, body }) {
  if (!body) return null
  return (
    <div>
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      {subject && <div className="text-xs text-gray-400 mb-1 font-medium">Subject: {subject}</div>}
      <div className="bg-navy rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-data leading-relaxed">
        {body}
      </div>
    </div>
  )
}

export function InvestorDetailSheet({ investor, onClose }) {
  const enrich = useEnrichInvestor()
  const genOutreach = useGenerateInvestorOutreach()

  if (!investor) return null

  const isEnriched = !!investor.enrichment_data
  const hasOutreach = !!investor.outreach_draft
  const draft = parseOutreachDraft(investor.outreach_draft)
  const e = investor.enrichment_data || {}

  return (
    <Sheet open={!!investor} onClose={onClose} title={investor.firm_name}>
      <div className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="default">Tier {investor.tier} — {TIER_LABELS[investor.tier]}</Badge>
          <Badge variant="muted">{investor.investor_type}</Badge>
          {investor.liam_leads && <Badge variant="client">Liam Leads</Badge>}
          {e.fit_score > 0 && <Badge variant="default">Fit: {e.fit_score}</Badge>}
          <Badge variant="muted">{investor.pipeline_stage?.replace(/_/g, ' ')}</Badge>
        </div>

        <div className="flex gap-2 flex-wrap">
          {!isEnriched && (
            <button
              onClick={() => enrich.mutate(investor.id)}
              disabled={enrich.isPending}
              className="px-3 py-1.5 text-xs rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium transition-colors"
            >
              {enrich.isPending ? 'Researching…' : 'Enrich'}
            </button>
          )}
          {isEnriched && !hasOutreach && (
            <button
              onClick={() => genOutreach.mutate(investor.id)}
              disabled={genOutreach.isPending}
              className="px-3 py-1.5 text-xs rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium transition-colors"
            >
              {genOutreach.isPending ? 'Drafting…' : 'Prepare Emails'}
            </button>
          )}
          {enrich.isError && <span className="text-xs text-red-400">Research failed — try again</span>}
          {genOutreach.isError && <span className="text-xs text-red-400">Draft failed — try again</span>}
        </div>

        <Field label="Contact" value={investor.contact_name} />
        <Field label="Contact Email" value={investor.contact_email} />
        <Field label="Check Size" value={investor.check_size_range} />

        {e.recommended_opener && (
          <div className="bg-emerald-900/30 border border-emerald-700/40 rounded p-3">
            <div className="text-xs text-emerald-400 uppercase tracking-wider mb-1">Recommended Opener</div>
            <div className="text-sm text-gray-200 italic">"{e.recommended_opener}"</div>
          </div>
        )}

        {e.contact_background && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Contact Background</div>
            <div className="text-sm text-gray-300">{e.contact_background}</div>
          </div>
        )}

        {e.apollo_profile?.employment_history?.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Career History</div>
            <div className="space-y-1">
              {e.apollo_profile.employment_history.map((job, i) => (
                <div key={i} className="flex gap-2 text-xs">
                  <span className="text-gray-500 font-data shrink-0">
                    {job.start}–{job.current ? 'now' : job.end}
                  </span>
                  <span className="text-gray-300">
                    {job.title} <span className="text-gray-500">at {job.company}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {e.firm_thesis && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Fund Thesis</div>
            <div className="text-sm text-gray-300">{e.firm_thesis}</div>
          </div>
        )}

        {e.pitch_angle && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Best Pitch Angle</div>
            <div className="text-sm text-gray-300">{e.pitch_angle}</div>
          </div>
        )}

        {e.recent_investments && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Recent Investments</div>
            <div className="text-sm text-gray-300">{e.recent_investments}</div>
          </div>
        )}

        {e.portfolio_hospitality?.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Portfolio — Adjacent</div>
            <div className="flex flex-wrap gap-1">
              {e.portfolio_hospitality.map((co, i) => <Badge key={i} variant="muted">{co}</Badge>)}
            </div>
          </div>
        )}

        <Field label="Why Fit" value={investor.why_fit} />
        <Field label="Warm Path" value={e.warm_path_notes || investor.warm_path} />

        {e.notes && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Research Notes</div>
            <div className="text-sm text-gray-300">{e.notes}</div>
          </div>
        )}

        {draft && (
          <div className="space-y-4 pt-2 border-t border-muted/30">
            <EmailDraft
              label="Email 1 Draft"
              subject={draft.email_1?.subject}
              body={draft.email_1?.body}
            />
            <EmailDraft
              label="Email 2 Draft"
              subject={draft.email_2?.subject}
              body={draft.email_2?.body}
            />
          </div>
        )}

        <Field label="Notes" value={investor.notes} />
        <Field label="LinkedIn" value={investor.contact_linkedin} />
        <Field label="Intake Form" value={investor.intake_form_url} />
      </div>
    </Sheet>
  )
}
