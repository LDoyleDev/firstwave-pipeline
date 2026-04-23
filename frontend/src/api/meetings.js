import { apiFetch } from './client'

export const fetchMeetings = (date) =>
  apiFetch(`/meetings${date ? `?date_filter=${date}` : ''}`)

export const fetchMeetingsToday = () => apiFetch('/meetings/today')

export const updateMeeting = (id, data) =>
  apiFetch(`/meetings/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
