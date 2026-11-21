import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { fetchBusinesses, fetchHealth, loadSyntheticDemo, type Business, type HealthResponse } from '../lib/api'

const journey = [
  ['Business intake', 'Create a profile and import evidence', '/businesses'],
  ['Evidence DNA', 'Reconcile records and trace source gaps', '/evidence-dna'],
  ['Trust Graph', 'Follow relationships back to records', '/trust-graph'],
  ['Financial Health', 'Review cash flow and obligations', '/financial-health'],
  ['CashFlow Twin', 'Test how shocks affect monthly cash', '/cashflow-twin'],
  ['Loan Options', 'Compare illustrative terms and monthly payments', '/loan-options'],
  ['Risk Insights', 'Review rules and capture an assessment snapshot', '/risk-insights'],
  ['Credit Passport', 'See the evidence and assumptions behind the snapshot', '/credit-passport'],
  ['Reviewer Desk', 'Record consent, follow-up and reviewer notes', '/reviewer-desk'],
]

const demoEntries = [
  { label: 'Business A — stronger evidence', name: 'Business A - Sunrise Foods' },
  { label: 'Business B — evidence gaps', name: 'Business B - Riverbend Repairs' },
]

export function OverviewPage() {
  const navigate = useNavigate()
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [health, setHealth] = useState<HealthResponse>()
  const [loading, setLoading] = useState(true)
  const [loadingDemo, setLoadingDemo] = useState(false)
  const [error, setError] = useState('')

  const refresh = async () => {
    setLoading(true)
    try {
      const [businessResult, healthResult] = await Promise.all([fetchBusinesses(), fetchHealth()])
      setBusinesses(businessResult)
      setHealth(healthResult)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not connect to the CREDWEAVE AI API.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [])

  const loadDemo = async () => {
    setLoadingDemo(true)
    try { await loadSyntheticDemo(); await refresh() } catch (err) { setError(err instanceof Error ? err.message : 'Could not load synthetic demo.') } finally { setLoadingDemo(false) }
  }

  const openDemoEntry = async (name: string) => {
    const existing = businesses.find((business) => business.name === name)
    if (existing) {
      navigate(`/businesses/${existing.id}/evidence-dna`)
      return
    }

    setLoadingDemo(true)
    setError('')
    try {
      await loadSyntheticDemo()
      const loadedBusinesses = await fetchBusinesses()
      setBusinesses(loadedBusinesses)
      const target = loadedBusinesses.find((business) => business.name === name)
      if (!target) throw new Error('The requested synthetic demo profile was not returned by the API.')
      navigate(`/businesses/${target.id}/evidence-dna`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open the synthetic demo profile.')
    } finally {
      setLoadingDemo(false)
    }
  }

  return (
    <main>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="text-3xl font-bold md:text-4xl">Credit review for small businesses</h1><p className="mt-3 max-w-2xl text-slate-600">Turn invoices, transactions, and obligations into a traceable Credit Passport for human lender review.</p></div>
        {health?.synthetic_demo && <button onClick={() => void loadDemo()} disabled={loadingDemo} className="rounded-lg bg-navy-900 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-navy-800 disabled:opacity-50">{loadingDemo ? 'Loading demo…' : 'Reset / load two synthetic businesses'}</button>}
      </div>

      {error && <p role="alert" className="mt-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}

      {health?.synthetic_demo && <section aria-label="Synthetic demo shortcuts" className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50/60 p-5">
        <h2 className="font-bold">Twin Business Challenge</h2>
        <p className="mt-1 text-sm text-slate-600">Compare two businesses with the same stated sales and different supporting evidence. Start with either profile in Evidence DNA.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          {demoEntries.map((entry) => {
            const business = businesses.find((candidate) => candidate.name === entry.name)
            return business
              ? <div key={entry.name} className="flex flex-wrap items-center gap-2"><Link to={`/businesses/${business.id}/evidence-dna`} className="rounded-lg border border-emerald-700 bg-white px-4 py-2.5 text-sm font-bold text-emerald-800 hover:bg-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-600">{entry.label}</Link><Link className="cw-button-secondary" aria-label={`Trust Graph for ${business.name}`} to={`/businesses/${business.id}/trust-graph`}>Trust Graph</Link><Link className="cw-button-secondary" aria-label={`Credit Passport for ${business.name}`} to={`/businesses/${business.id}/credit-passport`}>Credit Passport</Link></div>
              : <button key={entry.name} type="button" onClick={() => void openDemoEntry(entry.name)} disabled={loadingDemo} className="rounded-lg border border-emerald-700 bg-white px-4 py-2.5 text-sm font-bold text-emerald-800 hover:bg-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-600 disabled:opacity-50">{entry.label}</button>
          })}
        </div>
        <p className="mt-3 text-xs text-slate-500">Reset/load replaces only these two fixed synthetic profiles. Other businesses are retained.</p>
      </section>}

      <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-bold uppercase text-slate-400">Businesses</p><p className="mt-2 text-3xl font-bold">{loading ? '—' : businesses.length}</p><p className="mt-1 text-xs text-slate-500">Synthetic profiles in scope</p></article>
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-bold uppercase text-slate-400">API status</p><p className="mt-2 text-xl font-bold text-emerald-700">{health?.status === 'ok' ? 'Operational' : loading ? 'Checking…' : 'Unavailable'}</p><p className="mt-1 text-xs text-slate-500">{health ? `Service ${health.version}` : 'Waiting for backend'}</p></article>
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-bold uppercase text-slate-400">Decision mode</p><p className="mt-2 text-xl font-bold">Rules-only</p><p className="mt-1 text-xs text-slate-500">No predictive default score</p></article>
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-bold uppercase text-slate-400">Human control</p><p className="mt-2 text-xl font-bold">Required</p><p className="mt-1 text-xs text-slate-500">No automatic approval or denial</p></article>
      </div>

      <div className="mt-7 grid gap-6 lg:grid-cols-[1.35fr_.65fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Review journey</h2>
          <div className="mt-5 grid gap-3">
            {journey.map(([title, detail, route]) => <Link key={route} to={route} className="flex items-center gap-4 rounded-lg border border-slate-200 p-4 transition hover:border-emerald-300 hover:bg-emerald-50/40 focus:outline-none focus:ring-2 focus:ring-emerald-500"><span><strong className="block text-sm">{title}</strong><span className="mt-1 block text-sm text-slate-500">{detail}</span></span><span aria-hidden="true" className="ml-auto text-emerald-700">→</span></Link>)}
          </div>
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Synthetic businesses</h2>
          {loading ? <p role="status" className="mt-5 text-sm text-slate-500">Loading profiles…</p> : businesses.length === 0 ? <div className="mt-5 rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-600"><p>No synthetic businesses loaded.</p><button onClick={() => void loadDemo()} className="mt-3 font-bold text-emerald-700">Load demo data →</button></div> : <div className="mt-4 space-y-3">{businesses.map((business) => <Link key={business.id} to={`/businesses/${business.id}`} className="block rounded-lg border border-slate-200 p-4 transition hover:border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"><div className="flex justify-between gap-3"><strong className="text-sm">{business.name}</strong><span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-bold uppercase text-amber-700">{business.consent_status}</span></div><p className="mt-2 text-xs text-slate-500">{business.sector} · {business.city}</p></Link>)}</div>}
        </section>
      </div>

      <aside className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><strong>Important:</strong> All displayed records are marked SYNTHETIC or simulated. Cross-source matches show reconciliation consistency, not independent verification or transaction authenticity.</aside>
    </main>
  )
}
