import { apiFetch } from './client'

export const fetchLeads = (stage) =>
  apiFetch(`/leads${stage ? `?pipeline_stage=${stage}` : ''}`)

export const updateLead = (id, data) =>
  apiFetch(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

export const approveLead = (id) =>
  updateLead(id, { outreach_approved: true, pipeline_stage: 'approved' })

export const rejectLead = (id) =>
  updateLead(id, { pipeline_stage: 'closed_lost' })
