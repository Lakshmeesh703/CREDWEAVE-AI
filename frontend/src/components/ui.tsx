import { AlertCircle, Eye, EyeOff, Inbox } from 'lucide-react'
import { useId, useState, type InputHTMLAttributes, type ReactNode } from 'react'

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <header className="cw-page-header">
    <div><h1>{title}</h1>{description && <p>{description}</p>}</div>
    {action && <div className="flex flex-wrap gap-2">{action}</div>}
  </header>
}

export function MetricCard({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return <div className="cw-panel min-w-0">
    <dt className="text-sm font-semibold text-slate-600">{label}</dt>
    <dd className="mt-2 break-words text-2xl font-bold tabular-nums text-ink">{value}</dd>
    {detail && <dd className="mt-2 text-sm text-slate-600">{detail}</dd>}
  </div>
}

export function StatusBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'positive' | 'warning' | 'demo' }) {
  const colors = { neutral: 'bg-slate-100 text-slate-700', positive: 'bg-emerald-100 text-emerald-900', warning: 'bg-amber-100 text-amber-950', demo: 'bg-violet-100 text-violet-900' }
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${colors[tone]}`}>{children}</span>
}

export function EmptyState({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return <section className="cw-panel border-dashed text-sm text-slate-600">
    <Inbox aria-hidden="true" size={22} className="mb-3 text-teal" />
    <p>{children}</p>{action && <div className="mt-4">{action}</div>}
  </section>
}

export function ErrorState({ children }: { children: ReactNode }) {
  return <p role="alert" className="flex gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-900">
    <AlertCircle aria-hidden="true" size={17} className="mt-0.5 shrink-0" />{children}
  </p>
}

export function LoadingSkeleton({ children }: { children: ReactNode }) {
  return <div role="status" className="cw-panel text-sm text-slate-600">
    <p>{children}</p><div aria-hidden="true" className="mt-4 h-2 max-w-48 rounded-full bg-slate-200 motion-safe:animate-pulse" />
  </div>
}

export function PasswordField({ label = 'Password', ...props }: InputHTMLAttributes<HTMLInputElement> & { label?: string }) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  const Icon = visible ? EyeOff : Eye
  return <div className="grid gap-1.5 text-sm font-semibold">
    <label htmlFor={id}>{label}</label>
    <div className="relative">
      <input {...props} id={id} type={visible ? 'text' : 'password'} className="cw-input w-full pr-12" />
      <button type="button" aria-label={visible ? 'Hide password' : 'Show password'} aria-controls={id}
        onClick={() => setVisible(!visible)} className="absolute inset-y-1 right-1 grid w-10 place-items-center rounded-lg text-slate-600 hover:bg-slate-100">
        <Icon aria-hidden="true" size={18} />
      </button>
    </div>
  </div>
}
