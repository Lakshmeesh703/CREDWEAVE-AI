import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { EmptyState, ErrorState, LoadingSkeleton, PageHeader, StatusBadge } from './ui'
import { GatewayStatusCounts } from './VerifiedEvidencePage'
import { fetchEvidenceDna, type EvidenceDna, type EvidenceFinding } from '../lib/api'

function MetricCard({ label, score, detail }: { label: string; score: string; detail: string }) {
  return <section aria-label={label} className="cw-panel"><p className="text-sm font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-3 text-4xl font-bold text-ink">{score}</p><p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p></section>
}

function Finding({ finding, id }: { finding: EvidenceFinding; id: string }) {
  const [open, setOpen] = useState(false)
  return <li className="rounded-lg border border-slate-200 p-4"><button type="button" className="flex w-full items-center justify-between text-left" aria-expanded={open} onClick={() => setOpen(!open)}><span><strong className="text-ink">{finding.code}</strong><span className="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{finding.severity}</span></span><span className="text-sm text-teal">{open ? 'Hide details' : 'View details'}</span></button>{open && <div className="mt-4 space-y-2 text-sm leading-6 text-slate-600"><p>{finding.explanation}</p><p><strong>Check:</strong> {finding.check_performed}</p><p><strong>Follow-up:</strong> {finding.recommended_follow_up}</p>{finding.record_ids.length > 0 && <ul aria-label="Supporting records" className="space-y-1">{finding.record_ids.map((record) => <li key={record}><Link className="break-all font-semibold text-teal hover:underline" to={`/businesses/${id}/verified-evidence?record=${encodeURIComponent(record)}`}>{record}</Link></li>)}</ul>}{finding.linked_source_ids.length > 0 && <ul aria-label="Sources" className="space-y-1">{finding.linked_source_ids.map((source) => <li key={source}><Link className="break-all font-semibold text-teal hover:underline" to={`/businesses/${id}/verified-evidence?source=${encodeURIComponent(source)}`}>Source {source}</Link></li>)}</ul>}</div>}</li>
}

export function EvidenceDnaPage() {
  const { id = '' } = useParams()
  const [data, setData] = useState<EvidenceDna>()
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    void fetchEvidenceDna(id).then((result) => { if (active) setData(result) })
      .catch(() => { if (active) setError('Could not load Evidence DNA for this business.') })
    return () => { active = false }
  }, [id])
  if (error) return <main className="mx-auto max-w-4xl px-6 py-10"><ErrorState>{error}</ErrorState></main>
  if (!data) return <main className="mx-auto max-w-4xl px-6 py-10"><LoadingSkeleton>Loading Evidence DNA…</LoadingSkeleton></main>
  return <main className="space-y-6">
    <PageHeader title="Evidence DNA" description={`${data.business_name} · rule ${data.rule_version}`}
      action={data.provenance.synthetic && <><StatusBadge tone="demo">SYNTHETIC DEMO</StatusBadge><Link className="cw-button-secondary" to="/evidence-dna">Compare demo businesses</Link></>} />
    <div className="grid gap-4 md:grid-cols-2"><MetricCard label="Evidence completeness" score={data.evidence_completeness.denominator ? `${data.evidence_completeness.score}/100` : 'Not assessed'} detail={`${data.evidence_completeness.expected_periods.length} expected periods · ${data.evidence_completeness.denominator} checks`} /><MetricCard label="Evidence consistency" score={data.evidence_consistency.denominator ? `${data.evidence_consistency.score}/100` : 'Not assessed'} detail={`${data.evidence_consistency.matched} of ${data.evidence_consistency.denominator} eligible invoices matched`} /></div>
    <section className="cw-panel">
      <h2 className="text-xl font-bold">Verification status</h2>
      {data.gateway_status_counts && Object.keys(data.gateway_status_counts).length > 0
        ? <GatewayStatusCounts counts={data.gateway_status_counts} />
        : <p className="mt-2 text-sm text-slate-600">Not assessed. No Gateway results are available for this business.</p>}
      <details className="mt-3 text-sm"><summary className="cursor-pointer font-semibold">Source and matching indicators</summary>
        <dl className="mt-2 grid gap-2 sm:grid-cols-3">{Object.entries(data.verification_status).map(([label, count]) => <div key={label} className="rounded-lg bg-slate-50 p-2"><dt>{label.replace(/_/g, ' ')}</dt><dd className="font-bold">{count}</dd></div>)}</dl>
      </details>
      <Link className="mt-3 inline-block font-semibold text-teal hover:underline" to={`/businesses/${id}/verified-evidence`}>Open verification records →</Link>
    </section>
    <MetricCard label="Assessment confidence" score={data.assessment_confidence.label} detail={data.assessment_confidence.rationale} />
    <section className="cw-panel"><h2 className="text-xl font-bold text-ink">Claim-to-evidence trail</h2><p className="mt-2 text-sm text-slate-600">{data.claim_to_evidence.explanation}</p><p className="mt-3 text-sm text-slate-700">Reported monthly sales claim: <strong>{data.claim_to_evidence.reported_amount_inr == null ? 'Not recorded' : `₹${data.claim_to_evidence.reported_amount_inr}`}</strong></p><div className="mt-3 grid gap-2 text-sm text-slate-600 md:grid-cols-3">{Object.entries(data.claim_to_evidence.observed_monthly_credit_inr).map(([period, amount]) => <div key={period} className="rounded bg-slate-50 p-2">{period}: ₹{amount}</div>)}</div></section>
    <section className="cw-panel"><h2 className="text-xl font-bold text-ink">Findings and follow-up</h2><div className="mt-4">{data.findings.length ? <ul className="space-y-3">{data.findings.map((finding, index) => <Finding key={`${finding.code}-${index}`} finding={finding} id={id} />)}</ul> : <EmptyState>No checks have identified evidence gaps in the available records.</EmptyState>}</div></section>
    <section className="mt-6 rounded-xl bg-slate-50 p-5 text-sm text-slate-600"><h2 className="font-bold text-ink">Limitations</h2><ul className="mt-2 list-disc space-y-1 pl-5">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
  </main>
}
