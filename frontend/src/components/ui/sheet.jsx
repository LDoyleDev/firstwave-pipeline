import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

export function Sheet({ open, onClose, title, children, className }) {
  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/60" onClick={onClose} />
      <div className={cn('fixed right-0 top-0 z-50 h-full w-[520px] bg-charcoal border-l border-muted/50 flex flex-col shadow-2xl', className)}>
        <div className="flex items-center justify-between border-b border-muted/50 px-6 py-4">
          <h2 className="text-sm font-medium text-white">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </div>
    </>
  )
}
