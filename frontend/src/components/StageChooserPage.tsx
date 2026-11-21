import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { fetchBusinesses, fetchEvidenceDna, type Business, type EvidenceDna } from '../lib/api'
import { businessStagePath, businessStages } from '../lib/businessRoutes'

import { LoadingSkeleton, PageHeader, StatusBadge } from './ui'

const titles: Record<string, { title: string; description: string }> = {
  '/data-sources': { title: 'Data Sources', description: 'Inspect and upload evidence for a selected synthetic business.' },
  '/verified-evidence': { title: 'Verified Evidence Gateway', description: 'Inspect original sources and the history behind each verification status.' },
  '/evidence-dna': { title: 'Evidence DNA', description: 'Choose a business to compare completeness, consistency, and confidence.' },
  '/trust-graph': { title: 'Trust Graph', description: 'Explore evidence-backed relationships and review anomalies.' },
  '/financial-health': { title: 'Financial Health', description: 'Review normalized monthly cash flow and coverage warnings.' },
  '/risk-insights': { title: 'Risk Insights', description: 'Review rules-only indicators; never an ML default prediction.' },
  '/cashflow-twin': { title: 'CashFlow Twin', description: 'Run deterministic scenario comparisons with available monthly history.' },
  '/loan-options': { title: 'Loan Options', description: 'Compare illustrative EMI and affordability scenarios for human review.' },
  '/credit-passport': { title: 'Credit Passport', description: 'Open the latest immutable lender review snapshot.' },
  '/reviewer-desk': { title: 'Reviewer Desk', description: 'Record manual review status, consent, findings, and audit comments.' },
}

export function StageChooserPage() {
  const location = useLocation()
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [comparison, setComparison] = useState<EvidenceDna[]>()
  const [comparisonError, setComparisonError] = useState(false)
  const content = titles[location.pathname] ?? titles['/evidence-dna']

  useEffect(() => {
    setLoading(true)
    fetchBusinesses()
      .then(setBusinesses)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load businesses.'))
      .finally(() => setLoading(false))
  }, [])

  const compare = location.pathname === '/evidence-dna'
  useEffect(() => {
    if (!compare || !businesses.length) return
    const pair = businesses.filter((business) => ['Business A - Sunrise Foods', 'Business B - Riverbend Repairs'].includes(business.name))
    if (pair.length !== 2) return
    let active = true
    void Promise.all(pair.map((business) => fetchEvidenceDna(business.id)))
      .then((values) => { if (active) setComparison(values.filter((item) => item.provenance.synthetic)) })
      .catch(() => { if (active) setComparisonError(true) })
    return () => { active = false }
  }, [businesses, compare])

  const suffix = businessStages.find((stage) => stage.to === location.pathname)?.suffix ?? '/evidence-dna'
  return (
    <main>
      <PageHeader title={content.title} description={content.description} action={<StatusBadge tone="demo">SYNTHETIC DEMO</StatusBadge>} />
      {compare && comparison?.length === 2 && <section className="mt-6 space-y-3" aria-labelledby="twin-comparison">
        <h2 id="twin-comparison" className="text-xl font-bold">Twin Business Challenge</h2>
        <div className="grid gap-3 sm:grid-cols-2">{comparison.map((item) => <article key={item.business_id} className="cw-panel">
          <h3 className="font-bold">{item.business_name}</h3>
          <dl className="mt-3 grid gap-2 text-sm"><div><dt>Stated monthly sales</dt><dd className="font-bold">{item.claim_to_evidence.reported_amount_inr ? `₹${item.claim_to_evidence.reported_amount_inr}` : 'Unavailable'}</dd></div>
            <div><dt>Evidence completeness</dt><dd className="font-bold">{item.evidence_completeness.denominator ? `${item.evidence_completeness.score}/100` : 'Not assessed'}</dd></div>
            <div><dt>Evidence consistency</dt><dd className="font-bold">{item.evidence_consistency.denominator ? `${item.evidence_consistency.score}/100` : 'Not assessed'}</dd></div>
          </dl>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link className="cw-button-secondary" to={businessStagePath(item.business_id, '/evidence-dna')}>Evidence DNA</Link>
            <Link className="cw-button-secondary" to={businessStagePath(item.business_id, '/trust-graph')}>Trust Graph</Link>
            <Link className="cw-button-secondary" to={businessStagePath(item.business_id, '/credit-passport')}>Credit Passport</Link>
          </div>
        </article>)}</div>
      </section>}
      {compare && comparisonError && <p className="mt-4 text-sm text-slate-600">Comparison is unavailable. You can still open each business below.</p>}
      {error && <p role="alert" className="mt-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">{error}</p>}
      {loading ? <div className="mt-6"><LoadingSkeleton>Loading businesses…</LoadingSkeleton></div> : businesses.length === 0 ? <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-8"><h2 className="font-bold">No businesses available</h2><p className="mt-2 text-sm text-slate-600">Load the synthetic demo or create a business before opening this stage.</p><Link to="/businesses" className="mt-4 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white">Go to Businesses</Link></div> : (
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {businesses.map((business) => (
            <Link
              key={business.id}
              to={businessStagePath(business.id, suffix)}
              className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Synthetic business</p><h2 className="mt-2 text-xl font-bold">{business.name}</h2></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs capitalize text-slate-600">{business.consent_status}</span></div>
              <p className="mt-3 text-sm text-slate-600">{business.sector} · {business.city} · {business.operating_months} months</p>
              <p className="mt-5 text-sm font-bold text-emerald-700 group-hover:underline">Open {content.title} →</p>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}
