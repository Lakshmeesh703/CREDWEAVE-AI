import { X } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'

export function EvidenceDrawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const label = useId()
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    const trigger = document.activeElement
    if (dialog?.showModal) dialog.showModal()
    else dialog?.setAttribute('open', '')
    return () => {
      if (dialog?.open) dialog.close?.()
      if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus()
    }
  }, [])

  return <dialog ref={ref} aria-labelledby={label} onCancel={(event) => { event.preventDefault(); onClose() }}
    className="fixed inset-y-0 left-auto right-0 m-0 h-full max-h-none w-full max-w-xl overflow-y-auto border-l border-slate-200 bg-mist p-4 text-ink shadow-2xl backdrop:bg-navy-950/60 sm:p-6">
    <header className="mb-4 flex items-center justify-between gap-3">
      <h2 id={label} className="text-xl font-bold">{title}</h2>
      <button type="button" className="cw-button-secondary" onClick={onClose} aria-label="Close dialog"><X aria-hidden="true" size={19} /></button>
    </header>
    {children}
  </dialog>
}
