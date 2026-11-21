import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, createAssessment, fetchLatestAssessment, type Assessment } from '../lib/api'

import { EmptyState, ErrorState, LoadingSkeleton, PageHeader, StatusBadge } from './ui'

const rulesDisclosure = 'Rules-based analysis — no trained predictive default model'
const indicatorLabels: Record<string, string> = {
  expense_to_inflow_ratio_percent: 'Expense-to-inflow ratio',
  debt_to_average_inflow_percent: 'Debt burden',
  negative_months: 'Negative cash-flow months',
  volatility_to_average_inflow_percent: 'Cash-flow variability',
  supplier_concentration_percent: 'Supplier concentration',
}

export function AssessmentPage() {
  const { id = '' } = useParams()
  const [assessment, setAssessment] = useState<Assessment>()
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    void fetchLatestAssessment(id).then((value) => { if (active) setAssessment(value) })
      .catch((err: Error) => {
        if (active && !(err instanceof ApiError && err.status === 404)) setError('Could not load the assessment for this business.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [id])

  const assess = async () => {
    setCreating(true)
    try { setAssessment(await createAssessment(id)); setError('') } catch (err) { setError(err instanceof ApiError && err.status === 422 ? 'Upload operating transactions before creating an assessment.' : 'Could not create an assessment. Please try again.') } finally { setCreating(false) }
  }

  if (loading) return <main><LoadingSkeleton>Loading assessment…</LoadingSkeleton></main>
  const generate = <button type="button" onClick={() => void assess()} disabled={creating} className="cw-button">{creating ? 'Assessing…' : assessment ? 'Create fresh snapshot' : 'Create assessment snapshot'}</button>
  if (!assessment) return <main className="space-y-5">
    <PageHeader title="Risk Insights" description={rulesDisclosure} action={generate} />
    <EmptyState action={<Link className="cw-button-secondary" to={`/businesses/${id}`}>Open Data Sources</Link>}>Upload operating transactions to create a dated snapshot for your Credit Passport.</EmptyState>
    {error && <ErrorState>{error}</ErrorState>}
  </main>

  const snapshot = assessment.snapshot
  return <main className="space-y-5">
    <PageHeader title="Risk Insights" description={rulesDisclosure} action={<>{generate}<Link className="cw-button-secondary" to={`/businesses/${id}/credit-passport`}>Open Credit Passport</Link></>} />
    <p><StatusBadge tone={assessment.status === 'draft' ? 'warning' : 'neutral'}>{assessment.status === 'draft' ? 'Draft · limited evidence' : 'Assessment ready for review'}</StatusBadge></p>
    {error && <ErrorState>{error}</ErrorState>}
    <div className="mt-5 rounded-lg bg-amber-50 p-4 text-sm text-amber-800">{snapshot.decision_boundary}</div>
    <div className="mt-6 grid gap-5 lg:grid-cols-3">
      <section className="cw-panel min-w-0"><h2 className="text-lg font-bold text-ink">Financial Indicators</h2><div className="mt-3 space-y-3">{snapshot.risk_indicators.map((item) => <details key={item.code} className="rounded border border-slate-200 p-3"><summary className="cursor-pointer font-semibold text-ink">{indicatorLabels[item.code] ?? item.code} <span className="ml-2 text-xs text-teal">{item.status}</span></summary><p className="mt-2 text-sm text-slate-600">{item.explanation}</p><p className="mt-1 text-sm">{item.value ?? 'Unavailable'} {item.value !== null && item.unit}</p><p className="mt-1 text-xs text-slate-500">Formula: {item.formula}</p></details>)}</div></section>
      <section className="cw-panel min-w-0"><h2 className="text-lg font-bold text-ink">Evidence Quality</h2><p className="mt-3 text-sm text-slate-600">Completeness: <strong>{snapshot.evidence_quality.completeness.denominator ? `${snapshot.evidence_quality.completeness.score}/100` : 'Not assessed'}</strong></p><p className="mt-2 text-sm text-slate-600">Consistency: <strong>{snapshot.evidence_quality.consistency.denominator ? `${snapshot.evidence_quality.consistency.score}/100` : 'Not assessed'}</strong></p><p className="mt-2 text-sm text-slate-600">Verification counts remain separate from risk.</p><ul className="mt-3 space-y-1 text-xs text-slate-500">{Object.entries(snapshot.evidence_quality.verification_status).map(([name, count]) => <li key={name}>{name}: {count}</li>)}</ul></section>
      <section className="cw-panel min-w-0"><h2 className="text-lg font-bold text-ink">Assessment Confidence</h2><p className="mt-3 text-2xl font-bold capitalize text-teal">{snapshot.assessment_confidence.label}</p><p className="mt-2 text-sm text-slate-600">{snapshot.assessment_confidence.rationale}</p><p className="mt-3 text-xs text-slate-500">{snapshot.assessment_confidence.derivation}</p></section>
    </div>
    <div className="mt-6 grid gap-5 md:grid-cols-3">{[['Key risk factors', snapshot.key_risk_factors], ['Mitigating factors', snapshot.mitigating_factors], ['Manual review items', [...snapshot.unknowns, ...snapshot.recommended_lender_questions]]].map(([title, items]) => <section key={String(title)} className="cw-panel min-w-0"><h2 className="font-bold text-ink">{String(title)}</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-600">{(items as string[]).map((item) => <li key={item}>{item}</li>)}</ul></section>)}</div>
    <details className="cw-panel"><summary className="cursor-pointer font-bold">Assumptions and limitations</summary>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{[...new Set([...(assessment.limitations ?? snapshot.financial_summary.limitations), ...snapshot.fairness_notes])].map((item) => <li key={item}>{item}</li>)}</ul>
    </details>
    <p className="mt-5 break-words text-xs text-slate-500">Immutable snapshot {assessment.assessment_id} · Rule {assessment.rule_version} · Created {assessment.created_at}</p>
  </main>
}
