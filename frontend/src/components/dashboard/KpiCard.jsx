import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'

export function KpiCard({ label, value, trend, trendLabel, alert, onClick, className }) {
  const isUp = trend > 0
  return (
    <Card
      className={cn('cursor-pointer hover:border-muted transition-colors', alert && 'border-red-500/50', className)}
      onClick={onClick}
    >
      <CardContent className="pt-5">
        <div className="text-xs text-gray-500 uppercase tracking-widest mb-2">{label}</div>
        <div className={cn('font-data text-3xl font-medium', alert ? 'text-red-400' : 'text-white')}>
          {value ?? '—'}
        </div>
        {trend !== undefined && (
          <div className={cn('flex items-center gap-1 mt-2 text-xs', isUp ? 'text-green-400' : 'text-gray-500')}>
            {isUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {trendLabel}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
