import { ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function NetworkArt() {
  return <svg aria-hidden="true" viewBox="0 0 460 360" className="w-full max-w-lg text-emerald-300">
    <defs><radialGradient id="network-halo"><stop stopColor="#2dd4bf" stopOpacity=".28" /><stop offset="1" stopColor="#2dd4bf" stopOpacity="0" /></radialGradient></defs>
    <circle cx="230" cy="180" r="172" fill="url(#network-halo)" />
    <g stroke="currentColor" fill="none">
      <circle cx="230" cy="180" r="145" opacity=".24" strokeDasharray="4 7" />
      <circle cx="230" cy="180" r="100" opacity=".35" />
      <path d="M230 180 100 92 194 41 230 180 360 85 394 202 230 180 314 315 155 289 230 180M100 92 68 225 155 289M360 85 314 315M194 41 360 85M68 225 230 180" opacity=".62" />
      <circle cx="230" cy="180" r="40" fill="#14413e" />
    </g>
    <g fill="currentColor"><circle cx="100" cy="92" r="7" /><circle cx="194" cy="41" r="5" /><circle cx="360" cy="85" r="8" /><circle cx="394" cy="202" r="6" /><circle cx="314" cy="315" r="8" /><circle cx="155" cy="289" r="8" /><circle cx="68" cy="225" r="5" /></g>
    <path d="M215 179l10 10 20-22" stroke="currentColor" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
}

export function Brand() {
  return <Link to="/" className="inline-flex items-center gap-2.5 text-sm font-extrabold tracking-wide">
    <span className="grid h-9 w-9 place-items-center rounded-lg bg-teal text-white"><ShieldCheck size={21} aria-hidden="true" /></span>
    CREDWEAVE AI
  </Link>
}

export function AuthLayout({ children }: { children: ReactNode }) {
  return <main className="min-h-screen bg-mist lg:grid lg:grid-cols-[minmax(320px,.85fr)_1.15fr]">
    <aside className="hidden min-h-screen bg-navy-950 text-white lg:flex lg:flex-col lg:justify-center lg:px-[12%]">
      <NetworkArt />
      <p className="text-3xl font-bold tracking-tight">Evidence you can trace</p>
      <p className="mt-3 max-w-sm leading-relaxed text-slate-300">Review original sources, see how the records connect, and choose what to share with a lender.</p>
    </aside>
    <div className="mx-auto w-full max-w-xl px-5 py-6 sm:px-10 sm:py-10">
      <Brand /><div className="cw-panel mt-5 sm:p-8">{children}</div>
    </div>
  </main>
}

