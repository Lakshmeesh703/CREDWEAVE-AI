import { ArrowRight, Check, Circle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { ApiError, fetchEvidenceDna, fetchLatestAssessment, fetchSources, fetchSummary, type Assessment, type Business } from '../lib/api'
import { businessStagePath } from '../lib/businessRoutes'
import { MetricCard, StatusBadge } from './ui'

export function OwnerProgress({ business }: { business: Business }) {
  const [insights, setInsights] = useState<{
    records?: Awaited<ReturnType<typeof fetchSummary>>
    evidence?: Awaited<ReturnType<typeof fetchEvidenceDna>>
    assessment?: Assessment | null
    sources?: Awaited<ReturnType<typeof fetchSources>>
  }>()
  useEffect(() => {
    let current = true
    void Promise.allSettled([fetchSummary(business.id), fetchEvidenceDna(business.id), fetchLatestAssessment(business.id), fetchSources(business.id)])
      .then(([records, evidence, assessment, sources]) => {
        if (!current) return
        setInsights({
          records: records.status === 'fulfilled' ? records.value : undefined,
          evidence: evidence.status === 'fulfilled' ? evidence.value : undefined,
          sources: sources.status === 'fulfilled' ? sources.value : undefined,
          assessment: assessment.status === 'fulfilled' ? assessment.value
            : assessment.reason instanceof ApiError && assessment.reason.status === 404 ? null : undefined,
        })
      })
    return () => { current = false }
  }, [business.id])

  const records = insights?.records
  const evidence = insights?.evidence
  const assessment = insights?.assessment
  const total = records && Object.entries(records.counts).filter(([kind]) => ['transactions', 'invoices', 'counterparties', 'obligations'].includes(kind))
    .reduce((sum, [, count]) => sum + count, 0)
  const consent = business.source_upload_consent ?? business.consent_status === 'granted'
  const gateway = evidence?.gateway_status_counts
  const requiresReview = gateway?.REQUIRES_REVIEW ?? (gateway ? 0 : undefined)
  const steps = [
    { label: 'Register business', done: true, suffix: '' },
    { label: 'Consent to processing', done: consent, suffix: '#upload-consent' },
    { label: 'Upload evidence', done: Boolean(total), suffix: '#upload-evidence' },
    { label: 'Review checks', done: Boolean(total && gateway) && requiresReview === 0, suffix: '/verified-evidence' },
    { label: 'Run analysis', done: Boolean(assessment), suffix: '/assess' },
    { label: 'Credit Passport', done: Boolean(assessment), suffix: '/credit-passport' },
    { label: 'Share with lender', done: business.passport_sharing_consent === true, suffix: assessment ? '/credit-passport#share-with-lender' : '#share-with-lender' },
  ]
  const next = steps.find((step) => !step.done)
  const path = (suffix: string) => businessStagePath(business.id, suffix)
  const metric = assessment?.snapshot.financial_summary.monthly.length ? assessment.snapshot.financial_summary.metrics.net_operating_cash_flow : undefined
  const activities = [
    ...(insights?.sources ?? []).map((source) => ({ key: source.id, label: source.source_label, date: source.imported_at, detail: source.parsing_status })),
    ...(assessment ? [{ key: assessment.assessment_id, label: 'Assessment snapshot', date: assessment.created_at, detail: assessment.status }] : []),
  ].sort((left, right) => right.date.localeCompare(left.date)).slice(0, 4)
  const unavailable = insights ? 'Unavailable' : 'Loading…'
  return <section aria-labelledby="owner-progress" className="space-y-4">
    <div className="cw-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h2 id="owner-progress" className="text-xl font-bold">{business.name}</h2><p className="mt-1 text-sm text-slate-600">{steps.filter((step) => step.done).length} of {steps.length} onboarding steps ready</p></div>
        {next && <Link to={path(next.suffix)} className="cw-button">{next.label}<ArrowRight aria-hidden="true" size={16} /></Link>}
      </div>
      <ol aria-label="Business onboarding progress" className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {steps.map(({ label, done, suffix }) => {
          const Icon = done ? Check : Circle
          return <li key={label}><Link className="flex min-h-11 items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm font-semibold hover:bg-emerald-50" to={path(suffix)}>
            <Icon size={16} aria-hidden="true" className={done ? 'shrink-0 text-teal' : 'shrink-0 text-slate-500'} />{label}<span className="sr-only">{done ? ', ready' : ', not complete'}</span>
          </Link></li>
        })}
      </ol>
      <nav aria-label="Business shortcuts" className="mt-4 flex flex-wrap gap-3">
        <Link className="cw-button-secondary" to={path('#upload-evidence')}>Upload bank statement</Link>
        <Link className="cw-button-secondary" to={path('/verified-evidence')}>Review evidence</Link>
        {assessment && <Link className="cw-button-secondary" to={path('/credit-passport')}>View Credit Passport</Link>}
      </nav>
    </div>
    <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <MetricCard label="Uploaded records" value={total ?? unavailable} />
      <MetricCard label="Evidence completeness" value={evidence?.evidence_completeness.denominator ? `${evidence.evidence_completeness.score}/100` : evidence ? 'Not assessed' : unavailable} />
      <MetricCard label="Evidence consistency" value={evidence?.evidence_consistency.denominator ? `${evidence.evidence_consistency.score}/100` : evidence ? 'Not assessed' : unavailable} />
      <MetricCard label="Verification items requiring review" value={requiresReview ?? unavailable} detail={gateway?.SOURCE_VERIFIED ? `${gateway.SOURCE_VERIFIED} institution-sourced records` : undefined} />
      <MetricCard label="Credit Passport" value={assessment ? <StatusBadge tone="positive">Available</StatusBadge> : assessment === null ? 'Not generated' : unavailable} detail={assessment && new Date(assessment.created_at).toLocaleDateString()} />
      {metric?.value != null && <MetricCard label="Net operating cash flow" value={`₹${metric.value}`} detail={metric.data_coverage} />}
    </dl>
    <section className="cw-panel">
      <h3 className="font-bold">Recent business activity</h3>
      {activities.length ? <ul className="mt-2 divide-y divide-slate-200">{activities.map((item) =>
        <li key={item.key} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 py-2 text-sm">
          <strong className="break-all">{item.label}</strong><span className="text-slate-600"><time dateTime={item.date}>{new Date(item.date).toLocaleDateString()}</time> · {item.detail}</span>
        </li>)}</ul> : <p className="mt-2 text-sm text-slate-600">{!insights ? 'Checking recent activity…' : insights.sources && assessment !== undefined ? 'No imports or assessments have been recorded yet.' : 'Activity is unavailable.'}</p>}
    </section>
  </section>
}
