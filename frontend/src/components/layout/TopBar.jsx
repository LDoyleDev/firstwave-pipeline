import { useState, useEffect } from 'react'
import { format } from 'date-fns'

export function TopBar({ title }) {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const berlinTime = time.toLocaleTimeString('en-GB', { timeZone: 'Europe/Berlin', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const berlinDate = time.toLocaleDateString('en-GB', { timeZone: 'Europe/Berlin', weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-muted/50 bg-charcoal/50">
      <h1 className="text-sm font-medium text-white">{title}</h1>
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>{berlinDate}</span>
        <span className="font-data text-gray-300">{berlinTime} BER</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Live
        </span>
      </div>
    </header>
  )
}
