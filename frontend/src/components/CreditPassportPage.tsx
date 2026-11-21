import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'

import { GatewayStatusCounts } from './VerifiedEvidencePage'
import { LenderSharing } from './LenderSharing'
import { EmptyState, ErrorState, LoadingSkeleton, StatusBadge } from './ui'
import { ApiError, fetchCreditPassport, type CreditPassport, type StressTest } from '../lib/api'

export function CreditPassportPage({ canAssess = true, demo = true }: { canAssess?: boolean; demo?: boolean }) {
  const { id = '' } = useParams()
  const { hash } = useLocation()
  const [passport, setPassport] = useState<CreditPassport>()
  const [error, setError] = useState('')
  const [missing, setMissing] = useState(false)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    let active = true
    void fetchCreditPassport(id).then((value) => { if (active) { setPassport(value); setError(''); setMissing(false) } })
      .catch((err: unknown) => {
        if (!active) return
        setPassport(undefined)
        if (err instanceof ApiError && err.status === 404) setMissing(true)
        else setError('Could not load the Credit Passport. Please try again.')
      })
    return () => { active = false }
  }, [id, revision])

  useEffect(() => {
    if (passport && hash === '#share-with-lender') document.getElementById('share-with-lender')?.scrollIntoView?.()
  }, [passport, hash])

  if (error || missing) return <main className="space-y-4">
    <h1 className="text-3xl font-bold">Credit Passport</h1>
    {missing ? <EmptyState action={canAssess && <Link className="cw-button" to={`/businesses/${id}/assess`}>Generate an assessment snapshot</Link>}>
      {canAssess ? 'A Credit Passport becomes available when you create an assessment.' : 'The report is unavailable. It may still need an assessment, or access may have changed.'}
    </EmptyState> : <><ErrorState>{error}</ErrorState><button className="cw-button-secondary" type="button" onClick={() => { setError(''); setRevision((value) => value + 1) }}>Retry</button></>}
  </main>
  if (!passport) return <main><LoadingSkeleton>Loading Credit Passport…</LoadingSkeleton></main>
  const { snapshot } = passport
  return <main className="passport mx-auto min-w-0 max-w-6xl text-ink">
    <div className="cw-page-header items-start">
      <div><p className="text-sm font-bold uppercase tracking-[0.18em] text-teal">CREDWEAVE AI · Credit Passport</p><h1 className="mt-2 text-4xl font-bold">{snapshot.business.name}</h1><p className="mt-2 text-slate-600">{snapshot.business.sector} · {snapshot.business.city} · {snapshot.business.operating_months} months in operation</p></div>
      <div className="min-w-0 sm:text-right">{demo && <StatusBadge tone="demo">SYNTHETIC DEMO</StatusBadge>}<p className="rounded-full bg-amber-100 px-3 py-2 text-sm font-bold text-amber-800">{passport.status}</p><p className="mt-2 break-all text-xs text-slate-600">Assessment {passport.assessment_id}<br />{new Date(passport.created_at).toLocaleString()} · {passport.passport_version}</p><button disabled={!passport.export.allowed} title={passport.export.blocked_reason ?? undefined} onClick={() => window.print()} className="no-print cw-button-secondary mt-3">Print / Save PDF</button>{!passport.export.allowed && <p className="no-print mt-2 max-w-xs text-xs text-amber-700">{passport.export.blocked_reason}</p>}</div>
    </div>
    <section className="mt-6 rounded-xl bg-amber-50 p-5"><h2 className="font-bold text-amber-900">Important disclosures</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">{passport.disclosures.map((item) => <li key={item}>{item}</li>)}</ul></section>
    <div className="mt-6 grid gap-5 lg:grid-cols-2">
      <section className="cw-panel min-w-0"><h2 className="text-lg font-bold">Evidence DNA</h2><p className="mt-3">Completeness: <strong>{snapshot.evidence_dna.evidence_completeness.denominator ? `${snapshot.evidence_dna.evidence_completeness.score}/100` : 'Not assessed'}</strong></p><p>Consistency: <strong>{snapshot.evidence_dna.evidence_consistency.denominator ? `${snapshot.evidence_dna.evidence_consistency.score}/100` : 'Not assessed'}</strong></p><p>Confidence: <strong>{snapshot.evidence_dna.assessment_confidence.label}</strong></p><ul className="mt-3 space-y-1 text-sm text-slate-600">{Object.entries(snapshot.evidence_dna.verification_status).map(([key, value]) => <li key={key}>{key}: {value}</li>)}</ul><p className="mt-3 text-xs text-slate-500">{snapshot.evidence_dna.claim_to_evidence.explanation}</p></section>
      <section className="cw-panel min-w-0"><h2 className="text-lg font-bold">Source inventory and provenance</h2><p className="mt-2 text-sm text-slate-600">All sources captured in this immutable assessment snapshot.</p><ul className="mt-3 space-y-2 text-sm">{snapshot.source_inventory.map((source) => <li key={source.source_id} className="border-b pb-2"><Link className="break-all font-bold text-teal hover:underline" to={`/businesses/${id}/verified-evidence?source=${encodeURIComponent(source.source_id)}`}>{source.source_label}</Link> · {source.kind} · {source.synthetic ? 'SYNTHETIC' : 'Imported'}<span className="block break-all text-xs text-slate-500">{source.source_id} · {source.parsing_status}</span></li>)}</ul></section>
    </div>
    {snapshot.evidence_dna.gateway_status_counts && <section className="cw-panel mt-5 min-w-0">
      <h2 className="text-lg font-bold">Verified Evidence Gateway</h2>
      <GatewayStatusCounts counts={snapshot.evidence_dna.gateway_status_counts} />
    </section>}
    <section className="cw-panel mt-5 min-w-0"><h2 className="text-lg font-bold">Financial health and risk</h2><p className="mt-2 text-sm font-semibold text-slate-700">Rules-based analysis — no trained predictive default model</p><p className="mt-2 text-sm text-slate-600">Coverage: {snapshot.financial_summary.coverage.date_window ?? 'No observed window'}</p><div className="mt-4 grid gap-3 md:grid-cols-3">{snapshot.risk_indicators.map((item) => <article key={item.code} className="rounded border p-3"><p className="text-sm font-semibold">{item.code}</p><p className="mt-1 text-xl font-bold text-teal">{item.value ?? 'Unknown'} <span className="text-xs font-normal">{item.unit}</span></p><p className="mt-1 text-xs text-slate-600">{item.explanation}</p></article>)}</div></section>
    <section className="cw-panel mt-5">
      <h2 className="text-lg font-bold">Observed financial metrics</h2>
      {snapshot.financial_summary.monthly.length ? <dl className="mt-3 grid gap-3 sm:grid-cols-3">
        {([['total_inflows', 'Operating inflows'], ['total_outflows', 'Operating outflows'], ['net_operating_cash_flow', 'Net operating cash flow']] as const).map(([key, label]) => {
          const metric = snapshot.financial_summary.metrics[key]
          return <div key={key} className="rounded-lg bg-slate-50 p-3"><dt className="text-sm text-slate-600">{label}</dt>
            <dd className="font-bold">{metric?.value == null ? 'Unavailable' : `₹${metric.value}`}</dd>
          </div>
        })}
      </dl> : <p className="mt-2 text-sm text-slate-600">No operating transaction history was captured in this snapshot.</p>}
    </section>
    <section className="cw-panel mt-5 min-w-0"><h2 className="text-lg font-bold">Trust Graph findings</h2><p className="mt-2 text-sm text-slate-600">Top supplier concentration: {snapshot.trust_graph.metrics.top_supplier_share_percent == null ? 'Unavailable' : `${snapshot.trust_graph.metrics.top_supplier_share_percent}%`}</p><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{snapshot.trust_graph.anomalies.map((item) => <li key={`${item.code}-${item.record_ids.join('-')}`}>{item.message} <span className="text-xs">({item.record_ids.length} linked records)</span></li>)}</ul></section>
    <section className="cw-panel mt-5 min-w-0"><h2 className="text-lg font-bold">CashFlow Twin scenarios</h2><div className="mt-3 grid gap-4 md:grid-cols-2">{([['Normal operations', snapshot.cashflow_twin.normal], ['Combined crisis', snapshot.cashflow_twin.combined_crisis]] as [string, StressTest][]).map(([label, twin]) => <article key={label} className="rounded border p-4"><h3 className="font-semibold">{label}</h3><p className="mt-2 text-sm">Minimum cash after EMI {twin.monthly.length ? `₹${twin.metrics.minimum_net_cash_after_emi_inr}` : 'unavailable'}</p><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-600">{twin.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul></article>)}</div></section>
    <section className="cw-panel mt-5 min-w-0"><h2 className="text-lg font-bold">Illustrative loan options</h2>
      {snapshot.loan_options.requested_principal_inr && <p className="mt-2 text-sm text-slate-700">₹{snapshot.loan_options.requested_principal_inr} principal · {snapshot.loan_options.annual_interest_rate_pct}% annual interest · ₹{snapshot.loan_options.origination_fee_inr} origination fee</p>}
      {snapshot.loan_options.options.length === 0 && <p className="mt-2 text-sm text-slate-600">No loan illustration is available in this snapshot.</p>}
      <div className="mt-3 grid gap-3 md:grid-cols-4">{snapshot.loan_options.options.map((option) => <article key={option.tenure_months} className="rounded border p-3"><p className="font-semibold">{option.tenure_months} months</p><p className="mt-1 text-xl font-bold">₹{option.emi_inr}</p><p className="text-xs text-slate-600">Interest ₹{option.interest_cost_inr}</p><p className="mt-2 text-xs font-semibold text-amber-700">{option.affordability_status}</p></article>)}</div></section>
    <div className="mt-6 grid gap-5 md:grid-cols-2"><section className="cw-panel min-w-0"><h2 className="font-bold">Strengths</h2><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{snapshot.mitigating_factors.map((item) => <li key={item}>{item}</li>)}</ul></section><section className="cw-panel min-w-0"><h2 className="font-bold">Unanswered questions and limitations</h2><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{[...snapshot.unknowns, ...snapshot.recommended_lender_questions, ...snapshot.financial_summary.limitations].map((item) => <li key={item}>{item}</li>)}</ul></section></div>
    <section className="cw-panel mt-5"><h2 className="font-bold">Human review</h2>
      <p className="mt-2 text-sm text-slate-600">{passport.latest_review
        ? <><span className="capitalize">{passport.latest_review.status.replace(/_/g, ' ')}</span> · {new Date(passport.latest_review.updated_at).toLocaleString()}</>
        : 'No review has been recorded for this assessment.'}</p>
      <Link className="no-print mt-3 inline-block font-semibold text-teal hover:underline" to={`/businesses/${id}/review`}>Open review history</Link>
    </section>
    {canAssess && !demo && <div className="no-print mt-5"><LenderSharing businessId={id} onChange={() => {
      setPassport((current) => current ? { ...current, export: { ...current.export, allowed: false, blocked_reason: 'Checking sharing consent…' } } : current)
      setRevision((value) => value + 1)
    }} /></div>}
    <p className="mt-6 text-xs text-slate-500">Rule version: {passport.rule_version} · Snapshot values are not silently refreshed. Create a new assessment after source data changes.</p>
    {canAssess && <Link className="no-print mt-5 inline-block text-sm font-semibold text-teal hover:underline" to={`/businesses/${id}/assess`}>Return to assessment</Link>}
  </main>
}
