import { apiFetch } from './client'

export const fetchInvestors = (tier, stage) => {
  const params = new URLSearchParams()
  if (tier)  params.append('tier', tier)
  if (stage) params.append('pipeline_stage', stage)
  const qs = params.toString()
  return apiFetch(`/investors${qs ? `?${qs}` : ''}`)
}

export const updateInvestor = (id, data) =>
  apiFetch(`/investors/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

export const approveInvestor = (id) =>
  updateInvestor(id, { outreach_approved: true, pipeline_stage: 'ready_to_contact' })

export const rejectInvestor = (id) =>
  updateInvestor(id, { pipeline_stage: 'pass' })

export const enrichInvestor = (id) =>
  apiFetch(`/investors/${id}/enrich`, { method: 'POST' })

export const generateInvestorOutreach = (id) =>
  apiFetch(`/investors/${id}/generate-outreach`, { method: 'POST' })
