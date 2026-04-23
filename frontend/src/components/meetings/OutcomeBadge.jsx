import { Badge } from '@/components/ui/badge'
const MAP = { hot: 'hot', warm: 'warm', cold: 'cold', dead: 'muted', won: 'success' }
export function OutcomeBadge({ outcome }) {
  if (!outcome) return null
  return <Badge variant={MAP[outcome] ?? 'muted'}>{outcome.toUpperCase()}</Badge>
}
