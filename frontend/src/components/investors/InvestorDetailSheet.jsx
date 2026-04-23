import { Sheet } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { TIER_LABELS } from '@/lib/constants'

function Field({ label, value }) {
  if (!value) return null
  return (
    <div className="mb-3">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm text-gray-200">{value}</div>
    </div>
  )
}

export function InvestorDetailSheet({ investor, onClose }) {
  if (!investor) return null
  return (
    <Sheet open={!!investor} onClose={onClose} title={investor.firm_name}>
      <div className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="default">Tier {investor.tier} — {TIER_LABELS[investor.tier]}</Badge>
          <Badge variant="muted">{investor.investor_type}</Badge>
          {investor.liam_leads && <Badge variant="client">Liam Leads</Badge>}
        </div>
        <Field label="Stage" value={investor.pipeline_stage?.replace('_',' ')} />
        <Field label="Contact" value={investor.contact_name} />
        <Field label="Contact Email" value={investor.contact_email} />
        <Field label="Why Fit" value={investor.why_fit} />
        <Field label="Check Size" value={investor.check_size_range} />
        <Field label="Warm Path" value={investor.warm_path} />
        {investor.outreach_draft && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Outreach Draft</div>
            <div className="bg-navy rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-data leading-relaxed">
              {investor.outreach_draft}
            </div>
          </div>
        )}
        <Field label="Notes" value={investor.notes} />
        <Field label="Intake Form" value={investor.intake_form_url} />
        <Field label="LinkedIn" value={investor.contact_linkedin} />
      </div>
    </Sheet>
  )
}
