export const CLIENT_STAGES = [
  'discovered', 'enriched', 'review_queue', 'approved',
  'contacted', 'replied', 'meeting_booked', 'met',
  'follow_up', 'closed_won', 'closed_lost',
]

export const CLIENT_STAGE_LABELS = {
  discovered: 'Discovered', enriched: 'Enriched', review_queue: 'Review',
  approved: 'Approved', contacted: 'Contacted', replied: 'Replied',
  meeting_booked: 'Booked', met: 'Met', follow_up: 'Follow-Up',
  closed_won: 'Won', closed_lost: 'Lost',
}

export const INVESTOR_STAGES = [
  'identified', 'research_needed', 'ready_to_contact', 'contacted',
  'replied', 'meeting_booked', 'met', 'term_sheet', 'closed', 'pass',
]

export const INVESTOR_STAGE_LABELS = {
  identified: 'Identified', research_needed: 'Research', ready_to_contact: 'Ready',
  contacted: 'Contacted', replied: 'Replied', meeting_booked: 'Booked',
  met: 'Met', term_sheet: 'Term Sheet', closed: 'Closed', pass: 'Pass',
}

export const WARMTH_COLORS = {
  cold: '#64748b',
  warm: '#f59e0b',
  hot:  '#ef4444',
}

export const OUTCOME_COLORS = {
  hot:  '#ef4444',
  warm: '#f59e0b',
  cold: '#64748b',
  dead: '#374151',
  won:  '#22c55e',
}

export const STAGE_COLORS = {
  discovered: '#64748b', enriched: '#6366f1', review_queue: '#f59e0b',
  approved: '#3b82f6', contacted: '#2563eb', replied: '#22d3ee',
  meeting_booked: '#a78bfa', met: '#34d399', follow_up: '#fb923c',
  closed_won: '#22c55e', closed_lost: '#ef4444',
}

export const TIER_LABELS = {
  1: 'Hospitality VCs',
  2: 'Vertical AI / Pre-Seed',
  3: 'Accelerators',
  4: 'Enterprise AI / CX',
  5: 'European VCs',
  6: 'Angels',
}

export const SLOT_TIMES = { 1: '10:30', 2: '10:50', 3: '11:10' }

export const IS_PRODUCTION = import.meta.env.VITE_APP_ENV === 'production'
