import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

export function Dialog({ open, onClose, title, children, className }) {
  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/70" onClick={onClose} />
      <div className={cn('fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-charcoal border border-muted/50 rounded-lg shadow-2xl', className)}>
        <div className="flex items-center justify-between border-b border-muted/50 px-6 py-4">
          <h2 className="text-sm font-medium text-white">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </>
  )
}
