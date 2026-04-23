import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { useRealtimeUpdates } from '@/hooks/useRealtimeUpdates'

const PAGE_TITLES = {
  '/':          'Dashboard',
  '/clients':   'Client Pipeline',
  '/investors': 'Investor Pipeline',
  '/review':    'Review Queue',
  '/meetings':  'Meetings',
  '/analytics': 'Analytics',
  '/voice':     'Voice Log',
}

export function AppShell() {
  useRealtimeUpdates()
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? 'FirstWave Pipeline'

  return (
    <div className="flex min-h-screen bg-navy">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar title={title} />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
