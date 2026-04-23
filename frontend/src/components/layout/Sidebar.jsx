import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, TrendingUp, CheckSquare, Calendar, Mic, BarChart2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePipelineStats } from '@/hooks/usePipelineStats'

const links = [
  { to: '/',          label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/clients',   label: 'Clients',     icon: Users },
  { to: '/investors', label: 'Investors',   icon: TrendingUp },
  { to: '/review',    label: 'Review Queue', icon: CheckSquare, badge: true },
  { to: '/meetings',  label: 'Meetings',    icon: Calendar },
  { to: '/analytics', label: 'Analytics',   icon: BarChart2 },
  { to: '/voice',     label: 'Voice Log',   icon: Mic },
]

export function Sidebar() {
  const stats = usePipelineStats()

  return (
    <aside className="flex flex-col w-56 shrink-0 bg-charcoal border-r border-muted/50 min-h-screen">
      <div className="px-5 py-5 border-b border-muted/50">
        <div className="text-xs font-data font-medium text-accent tracking-widest uppercase">FirstWave</div>
        <div className="text-xs text-gray-500 mt-0.5">Pipeline OS</div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {links.map(({ to, label, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors group',
                isActive
                  ? 'bg-accent/15 text-white'
                  : 'text-gray-400 hover:bg-muted/30 hover:text-white',
              )
            }
          >
            <Icon size={15} className="shrink-0" />
            <span className="flex-1">{label}</span>
            {badge && stats.reviewQueue.total > 0 && (
              <span className={cn(
                'font-data text-xs px-1.5 py-0.5 rounded',
                stats.reviewQueue.total > 5 ? 'bg-red-500/20 text-red-400' : 'bg-accent/20 text-accent',
              )}>
                {stats.reviewQueue.total}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-muted/50 text-xs text-gray-600">
        <div>Liam Doyle</div>
        <div className="font-data">liam@firstwaveai.com</div>
      </div>
    </aside>
  )
}
