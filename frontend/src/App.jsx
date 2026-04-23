import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import Dashboard  from '@/pages/Dashboard'
import Clients    from '@/pages/Clients'
import Investors  from '@/pages/Investors'
import Review     from '@/pages/Review'
import Meetings   from '@/pages/Meetings'
import Analytics  from '@/pages/Analytics'
import Voice      from '@/pages/Voice'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index          element={<Dashboard />} />
        <Route path="clients"   element={<Clients />} />
        <Route path="investors" element={<Investors />} />
        <Route path="review"    element={<Review />} />
        <Route path="meetings"  element={<Meetings />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="voice"     element={<Voice />} />
        <Route path="*"         element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
